"""Shared text model and measured capacity gates for one-page assessment forms."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from pathlib import Path
import json, math, re
from datetime import date
from copy import deepcopy
from .list_layout import marker_advance_pt
from typing import Any
from PIL import ImageFont
from .content import ContentDataError as DataError, normalize_paragraph, normalize_content_block, runs_text, resolve_list_marker
from .font_files import resolve_font_files
from .typography import load_document_layout

KINDS = ('advisor-review','reviewer-review','defense-record','grade-assessment')
METADATA_FIELDS = ('title','student_name','student_id','college','major','advisor','advisor_title','reviewer','reviewer_title','defense_time','defense_location','recorder','leader')
SECTION_FIELDS = ('comments','division_of_work','suggested_grade','questions','members','final_grade','date')
GUIDANCE_FIELDS = ('comments','division_of_work','questions')

def layout(kind):
    if kind not in KINDS: raise DataError('unknown assessment form type')
    return load_document_layout(Path(__file__).resolve().parents[2]/kind/'spec/layout.json')

def overflow(path):
    raise DataError(f'SINGLE_PAGE_OVERFLOW: {path} 超出一页表格的固定区域，请减少内容；字号、边框与签名空间保持不变。')

def text(value,path,required=False):
    if not isinstance(value,str): raise DataError(f'{path} must be a string')
    if required and not value.strip(): raise DataError(f'{path} is required')
    if len(value)>20000: overflow(path)
    return value.strip()

def blocks(value,path):
    if not isinstance(value,list): raise DataError(f'{path} must be an array')
    result=[]
    for i,b in enumerate(value):
        if isinstance(b,dict) and b.get('type','paragraph') not in ('paragraph','ordered_list','unordered_list'): raise DataError(f'{path}[{i}] supports text paragraphs and lists only')
        normalized=normalize_content_block(b,f'{path}[{i}]',20000,max_list_depth=4)
        if any('type' in r for _,runs,_ in iter_paragraphs([normalized]) for r in runs): raise DataError(f'{path} supports text runs only')
        result.append(normalized)
    return result

def validate_data(raw,kind):
    layout(kind)
    if not isinstance(raw,dict) or set(raw)!= {'schema_version','metadata','sections'} or raw['schema_version']!='0.1': raise DataError('assessment data must contain schema_version 0.1, metadata and sections')
    m=raw['metadata'];s=raw['sections']
    if not isinstance(m,dict) or set(m)-set(METADATA_FIELDS): raise DataError('metadata contains unknown fields')
    if not isinstance(s,dict) or set(s)-{'editable_headings','writing_guidance'}!=set(SECTION_FIELDS): raise DataError('sections must contain the complete assessment fields')
    if 'editable_headings' in s and type(s['editable_headings']) is not bool:raise DataError('sections.editable_headings must be a boolean')
    metadata={k:text(m.get(k,''),'metadata.'+k,k in ('student_name','student_id','college','major')) for k in METADATA_FIELDS if k!='title'}
    metadata['title']=normalize_paragraph(m.get('title'),'metadata.title',20000)
    if any('type' in r for r in metadata['title']): raise DataError('metadata.title supports text runs only')
    sections={k:blocks(s[k],'sections.'+k) for k in ('comments','division_of_work')}
    if 'editable_headings' in s:sections['editable_headings']=s['editable_headings']
    if 'writing_guidance' in s:
        if not isinstance(s['writing_guidance'],dict) or set(s['writing_guidance'])-set(GUIDANCE_FIELDS):raise DataError('sections.writing_guidance must be a map with comments, division_of_work or questions keys')
        sections['writing_guidance']={key:normalize_guidance(value,'sections.writing_guidance.'+key) for key,value in s['writing_guidance'].items()}
    sections.update({k:text(s[k],'sections.'+k) for k in ('suggested_grade','final_grade','date')})
    if not isinstance(s['members'],list): raise DataError('sections.members must be an array')
    sections['members']=[text(v,f'sections.members[{i}]',True) for i,v in enumerate(s['members'])]
    if not isinstance(s['questions'],list): raise DataError('sections.questions must be an array')
    sections['questions']=[]
    for i,q in enumerate(s['questions']):
        if not isinstance(q,dict) or set(q)!= {'question','answer'}: raise DataError(f'sections.questions[{i}] requires question and answer')
        sections['questions'].append({k:blocks(q[k],f'sections.questions[{i}].{k}') for k in ('question','answer')})
    if sections['date']:
        format_date(sections['date'])
    if sections['final_grade']:
        if re.fullmatch(r'[0-9]+(?:\.[0-9]+)?',sections['final_grade']) is None: raise DataError('sections.final_grade must be a nonnegative decimal number')
        try:
            grade=Decimal(sections['final_grade'])
            if not grade.is_finite(): raise InvalidOperation()
            if len(sections['final_grade'])>64: overflow('sections.final_grade')
            final_grade(sections['final_grade'])
        except InvalidOperation as e: raise DataError('sections.final_grade must be a finite number') from e
    return {'schema_version':'0.1','metadata':metadata,'sections':sections}

def final_grade(value):
    if not value: return ''
    with localcontext() as context:
        context.prec=max(28,len(value)+2)
        return str(Decimal(value).quantize(Decimal('1'),rounding=ROUND_HALF_UP))

def iter_paragraphs(content,depth=0):
    for block in content:
        if block['type']=='paragraph': yield '',block['runs'],0
        else:
            for i,item in enumerate(block['items'],1):
                marker=resolve_list_marker(block['type'],item.get('marker'),i,depth+1,('•','◦','▪','▫'))
                yield marker,item['runs'],depth+1
                if item.get('children'): yield from iter_paragraphs([item['children']],depth+1)

def plain(value): return [{'text':value,'script':'normal','bold':False,'italic':False}]

def questions_content(data):
    result=[]
    for i,q in enumerate(data['sections']['questions'],1):
        for label,k in ((f'问题 {i}：','question'),('回答：','answer')):
            result.append({'type':'paragraph','runs':plain(label)})
            result.extend(q[k])
    return result

def prompt(kind):
    if kind=='advisor-review': return ('指导教师评语','（从选题价值和难度、工作量、工作态度、材料翔实性与论证严密性、创新性、撰写水平与规范性等方面进行评述）：')
    if kind=='reviewer-review': return ('评阅教师评语','（从选题价值和难度、工作量、材料翔实性与论证严密性、创新性、撰写的水平与规范性等方面进行评述）：')
    if kind=='grade-assessment': return ('答辩小组意见：','（从选题价值和难度、工作量、工作态度、论文的创新性、论证的严密性和论文撰写规范性、答辩中表现等方面给予评价）')
    return ('','答辩小组（学院答辩委员会）对学生毕业设计（论文）的陈述提出的问题及学生的回答情况：')

def writing_prompt(spec,key):
    r=next(r for r in spec['regions'] if r['key']==key)
    return r.get('label','')+r['value']+r.get('suffix',{}).get('text','')

def normalize_guidance(value,path):
    """Guidance is one rich paragraph; explicit null/empty is a real deletion."""
    if value is None or isinstance(value,str) and not value.strip():return []
    if isinstance(value,dict) and set(value)<= {'type','runs'} and value.get('type','paragraph')=='paragraph' and value.get('runs')==[]:return []
    result=normalize_paragraph(value,path,20000)
    if any('type' in r for r in result):raise DataError(path+' supports text runs only')
    return result

def has_guidance(data,key):
    return key in data['sections'].get('writing_guidance',{})

def guidance_runs(region,data):
    """Fixed labels and punctuation retain their own type, separate from notes."""
    result=[]
    if region.get('label'):
        style=region['guidance_style']['fixed_label']
        result.extend({**r,'role':'SimHei' if style['font'].startswith('heiti') else 'SimSun','size_pt':style['size_pt'],'bold':style['bold']} for r in plain(region['label']))
    result.extend({**r,'role':'SimSun','size_pt':region['size_pt']} for r in data['sections']['writing_guidance'][region['guidance_key']])
    if region.get('suffix'):
        style=region['guidance_style']['fixed_suffix']
        result.extend({**r,'role':'SimHei' if style['font'].startswith('heiti') else 'SimSun','size_pt':style['size_pt'],'bold':style['bold']} for r in plain(region['suffix']['text']))
    return result

def guidance_height(region,runs,measure):
    if not runs:return 0
    n=measure.lines(runs,region['width_mm'],region['size_pt'],region.get('first_line_indent_em',0)*region['size_pt'])
    return (max(r['size_pt'] for r in runs)+(n-1)*region['line_spacing_pt'])*25.4/72

def v2_heading(region,field,notes=None):
    result=deepcopy(region);result['source']='guidance';result['guidance_key']=field
    style=region['guidance_style']
    if result.get('label'):
        result['label_font']=style['fixed_label']['font'];result['label_size_pt']=style['fixed_label']['size_pt'];result['first_line_indent_em']=style['fixed_label']['first_line_indent_em']
    if result.get('suffix'):result['suffix']={**result['suffix'],**style['fixed_suffix']}
    result['font']=style['text']['font'];result['size_pt']=style['text']['size_pt']
    changed=bool(notes) and (runs_text(notes)!=region['value'] or any(r.get('bold') or r.get('italic') or r.get('script','normal')!='normal' for r in notes))
    if changed and 'punctuation' in style:
        punct=style['punctuation'];result.update(punct_style=punct['name'],punct_fixed_ratio=punct['fixed_punct_ratio'],punct_kerning_ratio=punct['kerning_total_ratio'],punct_optimize_kerning=punct['optimize_kerning'],punct_optimize_margin=punct['optimize_margin'])
    return result

def split_writing_prompt(content,spec,key):
    """Consume one real first paragraph only when its text is the source prompt.
    No prefix matching or hidden fallback: edited/deleted paragraphs stay edited.
    """
    if content and content[0]['type']=='paragraph' and runs_text(content[0]['runs'])==writing_prompt(spec,key) and all(not r.get('bold') and not r.get('italic') and r.get('script','normal')=='normal' for r in content[0]['runs']):
        return True,content[1:]
    return False,content

def _writing_plan_v1(data,kind,spec,fonts):
    """Resolve editable writing regions without mutating data or measured specs.
    Source-identical prompts retain the original mixed typography. Other text
    uses the common body style, starting where the former prompt began.
    """
    if not data['sections'].get('editable_headings',False):return spec,{}
    out=deepcopy(spec);overrides={};regions=out['regions'];measure=Measure(fonts)
    def region(key):return next(r for r in regions if r['key']==key)
    if kind!='defense-record':
        pairs=[('comments','prompt')]+([('division_of_work','division-label')] if kind=='advisor-review' else [])
        for field,key in pairs:
            matched,content=split_writing_prompt(data['sections'][field],spec,key)
            body=region(field);heading=region(key);overrides[field]=content
            if not matched:
                bottom=body['y_mm']+body['height_mm'];body['y_mm']=heading['y_mm'];body['height_mm']=bottom-body['y_mm'];regions.remove(heading)
    else:
        matched,intro=split_writing_prompt(data['sections']['comments'],spec,'questions-prompt')
        heading=region('questions-prompt');question=region('questions');bottom=question['y_mm']+question['height_mm']
        start=question['y_mm'] if matched else heading['y_mm']
        if not matched:regions.remove(heading)
        if intro:
            height=measure.blocks_height(intro,question['width_mm'],spec)
            ir={**question,'key':'editable-intro','source':'blocks','value':'comments','y_mm':start,'height_mm':height+.1}
            regions.insert(regions.index(question),ir);overrides['editable-intro']=intro
            start+=height+1
        question['y_mm']=start;question['height_mm']=bottom-start
        if question['height_mm']<0:overflow('sections.comments')
    return out,overrides

def identity_row_plan(data,spec,fonts):
    """Share unused horizontal space without changing type, rows or page margins.

    Opt-in measurements live in the document spec. Short/blank fields retain
    their source positions; both renderers consume the same adjusted tab stop.
    """
    config=spec.get('identity_row')
    if not config:return spec
    regions={r['key']:r for r in spec['regions']}
    college=regions[config['college_key']];major=regions[config['major_key']]
    measure=Measure(fonts);padding=config['measurement_padding_mm']
    def required(region):
        runs=region_runs(region,data)
        if any('\n' in r['text'] for r in runs):overflow('metadata.'+region['value'])
        return measure.width(runs,region['size_pt'])*25.4/72+padding
    college_width=required(college);major_width=required(major)
    right=config['right_mm'];gap=config['minimum_gap_mm']
    if (college_width<=college['width_mm'] and
        major_width<=min(major['width_mm'],right-major['x_mm'])):
        return spec
    minimum=college['x_mm']+college_width+gap
    maximum=right-major_width
    if minimum>maximum:
        overflow('metadata.'+('college' if college_width>college['width_mm'] else 'major'))
    out=deepcopy(spec);adjusted={r['key']:r for r in out['regions']}
    major_x=min(max(major['x_mm'],minimum),maximum)
    adjusted[college['key']]['width_mm']=major_x-college['x_mm']-gap
    adjusted[major['key']].update(x_mm=major_x,width_mm=right-major_x)
    out['word']['prelude']['college_tab_mm']+=major_x-major['x_mm']
    return out

def title_row_plan(data,spec,fonts):
    """Grow the measured title row, borrowing only flexible writing space.

    Font sizes and affected regions are document-specific; titles share an
    explicit line-height ratio and padding instead of inherited Word grids.
    Keep the page bottom, signature reserve and footer fixed in both outputs.
    """
    config=spec.get('title_row')
    if not config:return spec
    regions={r['key']:r for r in spec['regions']};title=regions[config['region_key']]
    measure=Measure(fonts);runs=region_runs(title,data)
    count=max(measure.lines(runs,title['width_mm'],title['size_pt']),
              measure.lines(runs,title['width_mm'],title['size_pt'],
                            cjk_latin_spacing_em=config.get('office_boundary_reserve_em',0)))
    text_height=(title['size_pt']+(count-1)*config['line_step_pt'])*25.4/72
    target=max(config['minimum_height_mm'],text_height+2*config['vertical_padding_mm'])
    delta=target-spec['table']['rows_mm'][0]
    if abs(delta)<.001:return spec
    body=regions[config['flexible_region_key']]
    if delta>body['height_mm']:overflow('metadata.title')
    out=deepcopy(spec);adjusted={r['key']:r for r in out['regions']}
    out['table']['rows_mm'][0]=target
    out['table']['rows_mm'][config['flexible_row_index']]-=delta
    out['word']['row_heights_twips']=[round(h*1440/25.4) for h in out['table']['rows_mm']]
    for key in config['row_region_keys']:adjusted[key]['height_mm']+=delta
    for key in config['shift_region_keys']:adjusted[key]['y_mm']+=delta
    adjusted[body['key']]['height_mm']-=delta
    row_end=spec['table']['top_mm']+spec['table']['rows_mm'][0]
    for segment in out['table']['vertical_segments_mm']:
        if segment[1]>=row_end-.001:segment[1]+=delta
        if segment[2]>=row_end-.001:segment[2]+=delta
    return out

def metadata_row_plan(data,spec,fonts):
    """Allow long metadata to wrap in its source columns, preserving footers."""
    config=spec.get('metadata_row')
    if not config:return spec
    regions={r['key']:r for r in spec['regions']};measure=Measure(fonts)
    counts={key:measure.lines(region_runs(regions[key],data),regions[key]['width_mm'],regions[key]['size_pt']) for key in config['field_keys']}
    limiting=max(counts,key=counts.get)
    target=config['minimum_height_mm']+max(0,counts[limiting]-config['base_lines'])*config['line_step_pt']*25.4/72
    index=config['row_index'];delta=target-spec['table']['rows_mm'][index]
    if abs(delta)<.001:return spec
    body=regions[config['flexible_region_key']]
    if delta>body['height_mm']:overflow('metadata.'+limiting)
    out=deepcopy(spec);adjusted={r['key']:r for r in out['regions']}
    out['table']['rows_mm'][index]=target
    out['table']['rows_mm'][config['flexible_row_index']]-=delta
    out['word']['row_heights_twips']=[round(h*1440/25.4) for h in out['table']['rows_mm']]
    for key in config['row_region_keys']:adjusted[key]['height_mm']+=delta
    for key in config['shift_region_keys']:adjusted[key]['y_mm']+=delta
    adjusted[body['key']]['height_mm']-=delta
    row_end=spec['table']['top_mm']+sum(spec['table']['rows_mm'][:index+1])
    for segment in out['table']['vertical_segments_mm']:
        if segment[1]>=row_end-.001:segment[1]+=delta
        if segment[2]>=row_end-.001:segment[2]+=delta
    return out

def writing_plan(data,kind,spec,fonts):
    """v2 explicit guidance supersedes v1 only for each present active key.
    Ordinary body paragraphs are never inspected or consumed in v2. Measured
    guidance changes body capacity while signature/member regions stay fixed.
    """
    spec=metadata_row_plan(data,title_row_plan(data,identity_row_plan(data,spec,fonts),fonts),fonts)
    out,overrides=_writing_plan_v1(data,kind,spec,fonts)
    if 'writing_guidance' not in data['sections']:return out,overrides
    out=deepcopy(out);measure=Measure(fonts)
    original={r['key']:r for r in spec['regions']}
    def install(field,key,body_key):
        nonlocal out
        regions=out['regions'];old=original[key];body=deepcopy(original[body_key]);heading=v2_heading(old,field,data['sections']['writing_guidance'][field])
        default_data={'sections':{'writing_guidance':{field:plain(old['value'])}}}
        default_height=guidance_height(heading,guidance_runs(heading,default_data),measure)
        height=guidance_height(heading,guidance_runs(heading,data),measure)
        gap=body['y_mm']-old['y_mm']-default_height
        end=body['y_mm']+body['height_mm'];start=old['y_mm']+height+gap
        body['y_mm']=start;body['height_mm']=end-start;heading['height_mm']=min(max(height+2,2),end-old['y_mm'])
        if body['height_mm']<0:overflow('sections.writing_guidance.'+field)
        regions[:]=[r for r in regions if r['key'] not in (key,body_key)]
        idx=next((i for i,r in enumerate(regions) if r['y_mm']>old['y_mm']),len(regions))
        regions[idx:idx]=[heading,body];overrides[body_key]=data['sections'][field]
        return height,start
    if kind!='defense-record':
        for field,key in [('comments','prompt')]+([('division_of_work','division-label')] if kind=='advisor-review' else []):
            if has_guidance(data,field):install(field,key,field)
    elif has_guidance(data,'questions'):
        # The source has an instruction paragraph, without a separate black
        # heading. Keep it whole, then preserve any additional intro body.
        out=deepcopy(spec);overrides={};regions=out['regions']
        head=next(r for r in regions if r['key']=='questions-prompt');question=next(r for r in regions if r['key']=='questions')
        heading=v2_heading(head,'questions',data['sections']['writing_guidance']['questions']);idx=regions.index(head);regions[idx]=heading
        default_data={'sections':{'writing_guidance':{'questions':plain(head['value'])}}}
        default_height=guidance_height(heading,guidance_runs(heading,default_data),measure)
        height=guidance_height(heading,guidance_runs(heading,data),measure)
        end=question['y_mm']+question['height_mm'];gap=question['y_mm']-head['y_mm']-default_height
        start=head['y_mm']+height+(gap if height else 0);heading['height_mm']=min(max(height+2,2),end-head['y_mm'])
        content=data['sections']['comments']
        if content:
            h=measure.blocks_height(content,question['width_mm'],spec)
            intro={**question,'key':'editable-intro','source':'blocks','value':'comments','y_mm':start,'height_mm':h+.1}
            regions.insert(regions.index(question),intro);overrides['editable-intro']=content;start+=h+1
        question['y_mm']=start;question['height_mm']=end-start
        if question['height_mm']<0:overflow('sections.writing_guidance.questions or sections.comments')
    return out,overrides

def resolved_fonts(spec):
    try: return resolve_font_files(spec['required_font_files'])
    except FileNotFoundError as e: raise FileNotFoundError('required official fonts are missing: '+str(e)) from e

def format_date(value):
    if not value: return ''
    try:
        actual=date.fromisoformat(value)
        if len(value)!=10: raise ValueError()
    except ValueError as e: raise DataError('sections.date must be a real date in YYYY-MM-DD format') from e
    return f'{actual.year}年{actual.month}月{actual.day}日'

def region_runs(region,data):
    source=region['source'];m=data['metadata'];s=data['sections']
    if source=='guidance':return guidance_runs(region,data)
    if source=='static': runs=plain(region['value'])
    elif source=='metadata': runs=m[region['value']] if region['value']=='title' else plain(m[region['value']])
    elif source=='section': runs=plain(s[region['value']])
    elif source=='grade': runs=plain(final_grade(s['final_grade']))
    elif source=='date': runs=plain(format_date(s['date']))
    elif source=='members': runs=plain('、'.join(s['members']))
    else: return []
    role={'songti':'SimSun','heiti':'SimHei','heitiBold':'SimHei'}
    runs=[{**r,'role':role[region['font']], 'size_pt':region['size_pt']} for r in runs]
    if region.get('prefix_runs'):
        runs=[{**r,'role':role[r['font']]} for r in region['prefix_runs']]+runs
    if region['label']: runs=[{**r,'role':role[region['label_font']], 'size_pt':region.get('label_size_pt',region['size_pt'])} for r in plain(region['label'])]+runs
    return runs

class Measure:
    """Official font advances and styled run wrapping, with measured list markers."""
    def __init__(self,fonts): self.fonts=fonts;self.cache={}
    def char_width(self,r,char,size,role='SimSun'):
        role=r.get('role',role);size=r.get('size_pt',size)
        if ord(char)<128 or char=='\u2009':
            role='Times New Roman'+(' Bold Italic' if r.get('bold') and r.get('italic') else ' Bold' if r.get('bold') or r.get('role')=='SimHeiBold' else ' Italic' if r.get('italic') else '')
        scale=0.7 if r.get('script') in ('super','sub') else 1
        key=(role,size*scale)
        if key not in self.cache:self.cache[key]=ImageFont.truetype(str(self.fonts[role]),round(size*scale*16))
        return self.cache[key].getlength(char)/16
    def width(self,runs,size,role='SimSun'):
        return sum(self.char_width(r,c,size,role) for r in runs for c in r['text'])
    def lines(self,runs,width_mm,size,indent_pt=0,continuation_indent_pt=0,*,cjk_latin_spacing_em=0):
        width=width_mm*72/25.4;used=indent_pt;n=1;previous=None
        for r in runs:
            for ch in r['text']:
                if ch=='\n':n+=1;used=continuation_indent_pt;previous=None;continue
                w=self.char_width(r,ch,size)
                # Some Office converters retain Asian/Latin spacing despite
                # autoSpaceDE/DN=false. Reserve height without changing text.
                boundary=previous is not None and ((ord(previous)>127 and ch.isascii() and ch.isalnum()) or (previous.isascii() and previous.isalnum() and ord(ch)>127))
                gap=cjk_latin_spacing_em*r.get('size_pt',size) if boundary else 0
                if w>width-continuation_indent_pt:return 100000
                if used+gap+w>width:n+=1;used=continuation_indent_pt;gap=0
                used+=gap+w;previous=ch
        return n
    def blocks_height(self,content,width_mm,spec):
        size=spec['typography']['body']['size_pt'];line=spec['paragraphs']['body_line_spacing_pt'];points=0
        for marker,runs,depth in iter_paragraphs(content):
            if depth:
                marker_width=marker_advance_pt(marker,size_pt=size,latin_font=self.fonts['Times New Roman'],cjk_font=self.fonts['SimSun'])
                indent=depth*2*size;usable=width_mm-(indent+marker_width)*25.4/72
                n=self.lines(runs,usable,size)
            else:n=self.lines(runs,width_mm,size,2*size)
            points+=n*line
        return points*25.4/72

def preflight(data,kind,spec=None,fonts=None):
    spec=spec or layout(kind);fonts=fonts or resolved_fonts(spec);measure=Measure(fonts)
    spec,overrides=writing_plan(data,kind,spec,fonts)
    for region in spec['regions']:
        source=region['source']
        if source in ('blocks','questions'):
            content=questions_content(data) if source=='questions' else overrides.get(region['key'],data['sections'][region['value']])
            if measure.blocks_height(content,region['width_mm'],spec)>region['height_mm']+.1:overflow('sections.'+('questions' if source=='questions' else region['value']))
        elif source!='static':
            runs=region_runs(region,data)
            if not any(r['text'] for r in runs):continue
            n=measure.lines(runs,region['width_mm'],region['size_pt'])
            if region.get('single_line') and n!=1:overflow('sections.'+region['key'])
            height=guidance_height(region,runs,measure) if source=='guidance' else (region['size_pt']+(n-1)*region['line_spacing_pt'])*25.4/72
            if height>region['height_mm']+.1:overflow(('metadata.' if source=='metadata' else 'sections.')+region.get('value',region['key']))
    return fonts
