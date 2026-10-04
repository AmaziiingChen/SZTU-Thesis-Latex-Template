"""Render fixed A4 assessment forms with measured TeX boxes and no clipping."""
from __future__ import annotations
import argparse,json,subprocess,shutil,sys
from pathlib import Path
from .assessment_forms import *
from .font_files import tex_font_parts,cjk_emphasis_options

def escape(value):
    return ''.join({'\\':r'\textbackslash{}','{':r'\{','}':r'\}','$':r'\$','&':r'\&','#':r'\#','%':r'\%','_':r'\_','~':r'\textasciitilde{}','^':r'\textasciicircum{}','\n':r'\newline{}'}.get(c,c) for c in value)

def rich(runs):
    parts=[]
    for r in runs:
        t=escape(r['text'])
        if r.get('bold'): t=r'\textbf{'+t+'}'
        if r.get('italic'): t=r'\textit{'+t+'}'
        if r.get('script')=='sub':t=r'\textsubscript{'+t+'}'
        if r.get('script')=='super':t=r'\textsuperscript{'+t+'}'
        parts.append(t)
    return ''.join(parts)

def rich_blocks(content,spec,fonts):
    result=[];size=spec['typography']['body']['size_pt'];unit=spec['paragraphs'].get('point_unit','pt')
    for marker,runs,depth in iter_paragraphs(content):
        if depth:
            advance=marker_advance_pt(marker,size_pt=size,latin_font=fonts['Times New Roman'],cjk_font=fonts['SimSun'])
            indent=depth*2*size+advance
            result.append(r'{\parindent=0pt\relax\leftskip='+str(indent)+unit+r'\relax\noindent\llap{'+escape(marker)+r'\hspace{0.16667em}}'+rich(runs)+r'\par}')
        else:result.append(r'{\parindent='+str(2*size)+unit+r'\relax '+rich(runs)+r'\par}')
    return '\n'.join(result)

def fonts_tex(fonts):
    d,f=tex_font_parts(fonts['SimSun']);hd,hf=tex_font_parts(fonts['SimHei']);ld,lf=tex_font_parts(fonts['Times New Roman'])
    return '\n'.join([r'\setmainfont[Path={'+ld+'},BoldFont={'+fonts['Times New Roman Bold'].name+'},ItalicFont={'+fonts['Times New Roman Italic'].name+'},BoldItalicFont={'+fonts['Times New Roman Bold Italic'].name+'}]{'+lf+'}',r'\setCJKmainfont['+cjk_emphasis_options(d)+']{'+f+'}',r'\newCJKfontfamily\songti['+cjk_emphasis_options(d)+']{'+f+'}',r'\newCJKfontfamily\heiti['+cjk_emphasis_options(hd)+']{'+hf+'}',r'\newfontfamily\assessmentTitleLatin['+cjk_emphasis_options(hd)+']{'+hf+'}',r'\newcommand{\heitiBold}{\heiti\bfseries}'])+'\n'

def body_tex(data,kind,spec,fonts):
    spec,overrides=writing_plan(data,kind,spec,fonts)
    table=spec['table'];x=table['left_mm'];y=table['top_mm'];w=table['width_mm'];bottom=y+sum(table['rows_mm']);pieces=[]
    def line(x1,y1,x2,y2):pieces.append(f'\\draw[line width={table["border_pt"]}pt] ({x1:.4f},{-y1:.4f}) -- ({x2:.4f},{-y2:.4f});')
    line(x,y,x+w,y);line(x,y,x,bottom);line(x+w,y,x+w,bottom)
    for h in table['rows_mm']:y+=h;line(x,y,x+w,y)
    for vx,y1,y2 in table['vertical_segments_mm']:line(vx,y1,vx,y2)
    for region in spec['regions']:
        source=region['source']
        if region.get('prefix_runs'):
            content=''.join('{\\'+('heiti' if r['role']=='SimHei' else 'songti')+r'\fontsize{'+str(r['size_pt'])+'bp}{'+str(region['line_spacing_pt'])+r'bp}\selectfont '+rich([r])+'}' for r in region_runs(region,data))
            if region.get('single_line'):content=r'\mbox{'+content+'}'
        elif source=='blocks':content=rich_blocks(overrides.get(region['key'],data['sections'][region['value']]),spec,fonts)
        elif source=='questions':content=rich_blocks(questions_content(data),spec,fonts)
        elif source=='date' and not data['sections']['date']:
            gaps=region.get('empty_gap_mm',[3,3]);content='年'+r'\hspace{'+str(gaps[0])+'mm}月'+r'\hspace{'+str(gaps[1])+'mm}日'
        else:
            if source=='metadata':value=rich(data['metadata']['title']) if region['value']=='title' else escape(data['metadata'][region['value']])
            elif source=='section':value=escape(data['sections'][region['value']])
            elif source=='grade':value=escape(final_grade(data['sections']['final_grade']))
            elif source=='date':value=r'{\xeCJKsetup{CJKecglue={}}'+escape(format_date(data['sections']['date']))+'}'
            elif source=='members':value=escape('、'.join(data['sections']['members']))
            elif source=='guidance':value=rich(data['sections']['writing_guidance'][region['guidance_key']])
            else:value=escape(region['value'])
            content=('{\\'+region['label_font']+r'\fontsize{'+str(region.get('label_size_pt',region['size_pt']))+'}{'+str(region['line_spacing_pt'])+r'}\selectfont '+escape(region['label'])+'}' if region['label'] else '')+value
        if not content:continue
        if region.get('suffix'):
            suffix=region['suffix'];content+='{\\'+suffix['font']+r'\fontsize{'+str(suffix['size_pt'])+region.get('point_unit','pt')+'}{'+str(region['line_spacing_pt'])+region.get('point_unit','pt')+r'}\selectfont '+escape(suffix['text'])+'}'
        if region.get('point_unit')=='bp':
            content=content.replace('\\fontsize{'+str(region.get('label_size_pt',region['size_pt']))+'}', '\\fontsize{'+str(region.get('label_size_pt',region['size_pt']))+'bp}')
        if region.get('punct_style'):content=r'{\xeCJKsetup{PunctStyle='+region['punct_style']+'}'+content+'}'
        if region.get('latin_font_role')=='cjk_label':content=r'{\assessmentTitleLatin\bfseries '+content+'}'
        if region.get('disable_cjk_latin_spacing'):content=r'{\xeCJKsetup{CJKecglue={}}'+content+'}'
        if region.get('first_line_indent_em'):
            content=r'{\parindent='+str(region['first_line_indent_em']*region['size_pt'])+r'pt\relax '+content+'}'
        args=[region['key']]+[str(region[k])+(region.get('point_unit','') if k=='size_pt' else '') for k in ('x_mm','y_mm','width_mm','height_mm','size_pt','font','alignment')]+[content]
        pieces.append('\\def\\AssessmentLineSpacing{'+str(region['line_spacing_pt'])+region.get('point_unit','')+'}'+('\\AssessmentCenteredBox' if region.get('vertical_alignment')=='center' else '\\AssessmentBox')+''.join('{'+a+'}' for a in args))
    return '\n'.join(pieces)+'\n'

MAIN=r'''\documentclass[a4paper,10.5pt]{article}
\usepackage[margin=0mm]{geometry}
\usepackage{fontspec,xeCJK,tikz}
\input{assessment-fonts.tex}
\pagestyle{empty}
\setlength{\parskip}{0pt}
\hfuzz=0pt
\newbox\AssessmentContent
\def\AssessmentLineSpacing{14}
\def\AssessmentVerticalCentered{0}
\newcommand{\AssessmentCenteredBox}[9]{\def\AssessmentVerticalCentered{1}\AssessmentBox{#1}{#2}{#3}{#4}{#5}{#6}{#7}{#8}{#9}\def\AssessmentVerticalCentered{0}}
\newcommand{\AssessmentBox}[9]{\node[anchor=north west,inner sep=0pt,outer sep=0pt] at (#2,-#3) {%
\setbox\AssessmentContent=\vbox{\hsize=#4mm\relax\normalfont\fontsize{#6}{\AssessmentLineSpacing}\selectfont\csname #7\endcsname\parindent=0pt\relax\parskip=0pt\relax\ifnum\pdfstrcmp{#8}{center}=0\centering\else\raggedright\fi #9\par}%
\ifdim\dimexpr\ht\AssessmentContent+\dp\AssessmentContent\relax>#5mm\errmessage{SINGLE_PAGE_OVERFLOW: #1}\fi
\ifnum\AssessmentVerticalCentered=1\vbox to #5mm{\vfil\box\AssessmentContent\vfil}\else\box\AssessmentContent\fi};}
\begin{document}
\null
\begin{tikzpicture}[remember picture,overlay,x=1mm,y=1mm]
\begin{scope}[shift={(current page.north west)}]
\input{body.tex}
\end{scope}
\end{tikzpicture}
\end{document}
'''

def render_bundle(kind,data_path,output_dir,*,overwrite=False,compile_pdf=False):
    output_dir=Path(output_dir);data_path=Path(data_path)
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:raise FileExistsError(f'output exists; pass --overwrite: {output_dir}')
    data=validate_data(json.loads(data_path.read_text()),kind);spec=layout(kind);fonts=preflight(data,kind,spec)
    output_dir.mkdir(parents=True,exist_ok=True)
    active,_=writing_plan(data,kind,spec,fonts);punct_styles={r['punct_style']:r for r in spec['regions']+active['regions'] if 'punct_fixed_ratio' in r}
    punct_declarations='\n'.join(r'\xeCJKDeclarePunctStyle{'+r['punct_style']+'}{fixed-punct-ratio='+str(r['punct_fixed_ratio'])+',optimize-margin='+str(r.get('punct_optimize_margin',True)).lower()+',kerning-total-ratio='+str(r.get('punct_kerning_ratio',.6))+',optimize-kerning='+str(r.get('punct_optimize_kerning',True)).lower()+'}' for r in punct_styles.values())
    (output_dir/'main.tex').write_text(MAIN.replace(r'\begin{document}',punct_declarations+'\n'+r'\begin{document}'),encoding='utf-8');(output_dir/'body.tex').write_text(body_tex(data,kind,spec,fonts),encoding='utf-8');(output_dir/'assessment-fonts.tex').write_text(fonts_tex(fonts),encoding='utf-8')
    if compile_pdf:
        cmd=['xelatex','-interaction=nonstopmode','-halt-on-error','main.tex']
        result=subprocess.run(cmd,cwd=output_dir,capture_output=True,text=True)
        if result.returncode == 0: result=subprocess.run(cmd,cwd=output_dir,capture_output=True,text=True)
        if result.returncode == 0 and 'Overfull \\hbox' in result.stdout:
            (output_dir/'main.pdf').unlink(missing_ok=True)
            raise DataError('SINGLE_PAGE_OVERFLOW: unbreakable text exceeds the fixed region; please shorten the content')
        if result.returncode:
            (output_dir/'main.pdf').unlink(missing_ok=True)
            if 'SINGLE_PAGE_OVERFLOW' in result.stdout:raise DataError(next(l for l in result.stdout.splitlines() if 'SINGLE_PAGE_OVERFLOW' in l))
            raise RuntimeError('LaTeX compile failed: '+result.stdout[-3000:])
        info=subprocess.run(['pdfinfo',str(output_dir/'main.pdf')],capture_output=True,text=True,check=True).stdout
        if not any(l.strip()=='Pages:           1' for l in info.splitlines()):
            (output_dir/'main.pdf').unlink(missing_ok=True);raise DataError('SINGLE_PAGE_OVERFLOW: generated PDF must contain exactly one page')
    return output_dir

def latex_cli(kind,base):
    parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,required=True);parser.add_argument('--output','--output-dir',dest='output',type=Path,required=True);parser.add_argument('--overwrite',action='store_true');parser.add_argument('--compile',action='store_true');args=parser.parse_args()
    try:output=render_bundle(kind,args.data,args.output,overwrite=args.overwrite,compile_pdf=args.compile)
    except (DataError,OSError,ValueError,RuntimeError) as e:print('error: '+str(e),file=sys.stderr);return 2
    print(output);return 0
