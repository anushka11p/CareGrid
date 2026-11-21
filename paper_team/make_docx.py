"""Build the Word version of the paper in IEEE conference layout: paper_team/CareGrid_paper.docx.

Layout follows the IEEE conference template (US Letter): margins 0.75 in top, 1 in bottom,
0.625 in sides; title block across the page, body in two 3.5 in columns 0.25 in apart; Times New
Roman 10 pt body, 24 pt title, 9 pt bold abstract and index terms, small-caps Roman-numeral section
headings, italic lettered subsections, numbered equations, "TABLE I" table titles, 8 pt captions,
table text and references. Full-width figures and tables sit in one-column sections.

Steps: compile main.tex once (tectonic, keeping main.aux and main.bbl) for citation, figure and
table numbers; render the TikZ diagram to PNG; rewrite main.tex into LaTeX that pandoc reads well;
run pandoc (equations become editable Word equations); apply the IEEE layout to the Word XML.
Needs tectonic, pdftoppm and pandoc on PATH:
    python paper_team/make_docx.py
"""
import pathlib
import re
import shutil
import subprocess
import tempfile
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "CareGrid_paper.docx"

# page geometry in twips (1 in = 1440)
PAGE_W, PAGE_H = 12240, 15840
M_TOP, M_BOTTOM, M_SIDE = 1080, 1440, 900
COL_GAP = 360
COL_W = (PAGE_W - 2 * M_SIDE - COL_GAP) // 2          # 5040 = 3.5 in
TEXT_W = PAGE_W - 2 * M_SIDE                          # 10440 = 7.25 in
EMU_PER_IN = 914400
WIDE = {"TABLE I", "TABLE III", "Fig. 3"}             # full-width floats (table* / figure* in LaTeX)
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
TNR = 'w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="Times New Roman" w:cs="Times New Roman"'


def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def cite_text(nums):
    """IEEE style: [1], [3]--[5]."""
    nums = sorted(set(nums))
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(f"[{nums[i]}]" if j - i < 2 else f"[{nums[i]}]--[{nums[j]}]")
        if 0 < j - i < 2:
            out.append(f"[{nums[j]}]")
        i = j + 1
    return ", ".join(out)


def bbl_items(bbl, bibnum):
    items = re.findall(r"\\bibitem\{([^}]*)\}\s*(.*?)(?=\\bibitem\{|\\end\{thebibliography\})", bbl, re.S)
    lines = []
    for key, text in items:
        text = re.sub(r"\\BIBentry(ALT|STD)interwordspacing\s*", "", text)
        text = re.sub(r"\s+", " ", text.replace("\\newblock", "")).strip()
        lines.append((bibnum[key], text))
    return sorted(lines)


# ---------------------------------------------------------------- LaTeX -> pandoc-friendly LaTeX
def prepare_source(tmp):
    aux = (tmp / "main.aux").read_text()
    bibnum = {k: int(n) for k, n in re.findall(r"\\bibcite\{([^}]*)\}\{(\d+)\}", aux)}
    labels = dict(re.findall(r"\\newlabel\{([^}]*)\}\{\{([^}]*)\}", aux))
    src = (tmp / "main.tex").read_text()

    # TikZ diagram -> PNG
    tikz = re.search(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", src, re.S).group(0)
    (tmp / "shield.tex").write_text(
        "\\documentclass[border=4pt]{standalone}\n\\usepackage{mathptmx}\n\\usepackage{tikz}\n"
        "\\usetikzlibrary{positioning,arrows.meta,fit}\n\\begin{document}\n" + tikz + "\n\\end{document}\n")
    run(["tectonic", "-X", "compile", "shield.tex"], tmp)
    run(["pdftoppm", "-png", "-r", "300", "-singlefile", "shield.pdf", "fig_shield"], tmp)
    src = src.replace(tikz, "\\includegraphics{fig_shield.png}")
    for f in (HERE / "figures").glob("fig_*.png"):
        shutil.copy(f, tmp)
    src = re.sub(r"\{(fig_[a-z]+)\.pdf\}", r"{\1.png}", src)
    src = re.sub(r"\\includegraphics(\[[^\]]*\])?\{fig_([a-z]+)\.png\}",
                 lambda m: f"\\includegraphics[width={'7in' if m.group(2) == 'case' else '3.45in'}]{{fig_{m.group(2)}.png}}", src)

    # tables inline
    for t in re.findall(r"\\input\{(tab_[a-z]+)\.tex\}", src):
        body = (tmp / f"{t}.tex").read_text().replace("table*", "table").replace("\\quad ", "-- ")
        body = re.sub(r"\\setlength\{[^}]*\}\{[^}]*\}|\\footnotesize|\\cmidrule\([^)]*\)\{[^}]*\}", "", body)
        src = src.replace(f"\\input{{{t}.tex}}", body)
    src = src.replace("\\begin{figure*}", "\\begin{figure}").replace("\\end{figure*}", "\\end{figure}")

    # numbered captions, cross-references and citations from the LaTeX build
    def number_caption(m):
        env, caption, label = m.group(1), m.group(2), m.group(3)
        prefix = f"Fig.~{labels[label]}. " if env == "figure" else f"TABLE {labels[label]}. "
        return m.group(0).replace(f"\\caption{{{caption}}}", f"\\caption{{{prefix}{caption}}}", 1)
    src = re.sub(r"\\begin\{(figure|table)\}.*?\\caption\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}\s*\\label\{([^}]*)\}.*?\\end\{\1\}",
                 number_caption, src, flags=re.S)
    src = re.sub(r"\\ref\{([^}]*)\}", lambda m: labels[m.group(1)], src)
    src = re.sub(r"\\label\{[^}]*\}", "", src)
    src = re.sub(r"\\cite\{([^}]*)\}", lambda m: cite_text(bibnum[k.strip()] for k in m.group(1).split(",")), src)

    # one equation per display, so each gets its own number as in the PDF
    src = re.sub(r"\\begin\{gather\}(.*?)\\end\{gather\}",
                 lambda m: "\n".join(f"\\begin{{equation}}{line.strip()}\\end{{equation}}"
                                     for line in m.group(1).split("\\\\")), src, flags=re.S)

    # section numbers as in IEEEtran
    sec = sub = 0

    def number_heading(m):
        nonlocal sec, sub
        if m.group(1) == "section":
            sec, sub = sec + 1, 0
            return f"\\section{{{ROMAN[sec - 1]}. {m.group(2)}}}"
        sub += 1
        return f"\\subsection{{{chr(64 + sub)}. {m.group(2)}}}"
    src = re.sub(r"\\(section|subsection)\{([^}]*)\}", number_heading, src)

    # title block, abstract, index terms
    thanks = re.search(r"\\thanks\{(.*?)\}\}\s*\n\s*\\maketitle", src, re.S).group(1)
    thanks = thanks.replace("$^{\\dagger}$", "\\textsuperscript{†}").replace("$^{*}$", "\\textsuperscript{*}")
    author = re.search(r"\\author\{.*?\\maketitle", src, re.S).group(0)
    src = src.replace(author, "\n\n".join([
        "\\author{Khrisha N\\textsuperscript{1,†}, Anushka Prasad\\textsuperscript{1,†}, "
        "Pushpa Mitra Ganesh\\textsuperscript{1,†} and P. Madhavan\\textsuperscript{2,*}}\n\\maketitle",
        "\\textsuperscript{1}\\textit{Department of Electronics and Computer Engineering}",
        "\\textsuperscript{2}\\textit{Department of Computing Technologies}",
        "\\textit{Faculty of Engineering and Technology, SRM Institute of Science and Technology}",
        "Kattankulathur, Chennai, India",
        "\\{kn9023, ap0362, pg5197, madhavap\\}@srmist.edu.in",
        thanks, ""]))
    src = re.sub(r"\\begin\{abstract\}(.*?)\\end\{abstract\}",
                 lambda m: "\\textbf{\\textit{Abstract}---" + m.group(1).strip() + "}", src, flags=re.S)
    src = re.sub(r"\\begin\{IEEEkeywords\}(.*?)\\end\{IEEEkeywords\}",
                 lambda m: "\\textbf{\\textit{Index Terms}---" + m.group(1).strip() + "}", src, flags=re.S)

    # lists as "1)" paragraphs (IEEE style; Word would also restart numbering after equations)
    def manual_numbers(m):
        items = re.split(r"\\item\s+", m.group(1))[1:]
        return "\n\n" + "\n\n".join(f"{i}) {it.strip()}" for i, it in enumerate(items, 1)) + "\n\n"
    src = re.sub(r"\\begin\{enumerate\}(.*?)\\end\{enumerate\}", manual_numbers, src, flags=re.S)

    src = re.sub(r"\\bstctlcite\{[^}]*\}|\\IEEEoverridecommandlockouts|\\noindent", "", src)
    src = src.replace("\\documentclass[conference]{IEEEtran}", "\\documentclass{article}")
    src = plain_symbols(src)
    refs = bbl_items((tmp / "main.bbl").read_text(), bibnum)
    src = re.sub(r"\\bibliographystyle\{[^}]*\}\s*\\bibliography\{[^}]*\}",
                 lambda m: "\\section*{References}\n\n" + "\n\n".join(f"[{n}] {t}" for n, t in refs), src)
    return src


SUB_MINUS = str.maketrans({"-": "\u2212"})


def plain_symbols(src):
    """Small math snippets as text, so they take the surrounding font and size (tables, captions)
    and render in any viewer; also forms Word lays out better."""
    reps = [
        (r"\$\^\{?\\circ\}?\$", "\u00b0"),
        (r"\$\^\{?\\dagger\}?\$", "\\textsuperscript{\u2020}"),
        (r"\$\^\{?\\ddagger\}?\$", "\\textsuperscript{\u2021}"),
        (r"PH\$_\{32\}\$", "PH\\textsubscript{32}"),
        (r"\$\\pm\$", "\u00b1"),
        (r"\$-\$", "\u2212"),
        (r"\$\\times\$", "\u00d7"),
        (r"\$\\Delta\$", "\u0394"),
        (r"\$\\alpha\$", "\u03b1"),
        (r"\$\\tau_\{90\}\$", "\u03c4\\textsubscript{90}"),
        (r"\$\\hat\\tau\$", "\u03c4\u0302"),
    ]
    for pat, rep in reps:
        src = re.sub(pat, lambda m, rep=rep: rep, src)
    src = re.sub(r"\$n=(\d+)\$", lambda m: "\\textit{n}\u2009=\u2009" + m.group(1), src)
    src = re.sub(r"\$\\tau_\{90\}=(\d+)\$", lambda m: "\u03c4\\textsubscript{90}\u2009=\u2009" + m.group(1), src)
    src = re.sub(r"\$([A-Za-z])\$", lambda m: "\\textit{" + m.group(1) + "}", src)
    src = re.sub(r"\$(\d+)\\times10\^\{(-?\d+)\}\$",
                 lambda m: f"{m.group(1)}\u00d710\\textsuperscript{{{m.group(2).translate(SUB_MINUS)}}}", src)
    src = re.sub(r"\\begin\{equation\}\s*T_\{h,t\+1\}.*?\\end\{equation\}",
                 lambda m: "\\begin{equation}\\begin{aligned}T_{h,t+1} = T_{h,t} + \\frac{1}{C_h}\\Big[\\frac{T^{o}_t - T_{h,t}}{R_h}"
                           " + a_h G_t \\\\ {}+ q_h - \\mathrm{COP}(T^{o}_t)\\,u_{h,t}\\Big]\\end{aligned}\\end{equation}",
                 src, flags=re.S)
    src = src.replace("\\tfrac", "\\frac").replace("\\mathrm{COP}", "\\operatorname{COP}")
    src = src.replace("\\mathrm{softmax}", "\\operatorname{softmax}")
    # aligned: drop the & markers (Word aligns them, other viewers print them)
    src = re.sub(r"\\begin\{aligned\}(.*?)\\end\{aligned\}",
                 lambda m: "\\begin{aligned}" + m.group(1).replace("&", "") + "\\end{aligned}", src, flags=re.S)
    return src


# ---------------------------------------------------------------- Word XML helpers
def blocks(body):
    """Split the body into top-level blocks (paragraphs, tables, sectPr, anything between)."""
    out, depth, start, pos = [], 0, None, 0
    for m in re.finditer(r"<(/?)(w:p|w:tbl|w:sectPr)(?=[\s>/])[^>]*?(/?)>", body):
        closing, selfclosing = m.group(1) == "/", m.group(3) == "/"
        if depth == 0 and not closing:
            if m.start() > pos:
                out.append(body[pos:m.start()])
            if selfclosing:
                out.append(m.group(0))
                pos = m.end()
                continue
            start = m.start()
        if selfclosing:
            continue
        depth += -1 if closing else 1
        if depth == 0:
            out.append(body[start:m.end()])
            pos = m.end()
    out.append(body[pos:])
    return out


def text_of(xml):
    return "".join(re.findall(r"<(?:w|m):t(?:\s[^>]*)?>([^<]*)</(?:w|m):t>", xml))


def style_of(p):
    m = re.search(r'<w:pStyle w:val="([^"]+)"', p)
    return m.group(1) if m else ""


def set_style(p, sid, extra=""):
    """Replace the paragraph's properties with a style (and optional direct formatting)."""
    ppr = f'<w:pPr><w:pStyle w:val="{sid}"/>{extra}</w:pPr>'
    if re.search(r"<w:pPr>.*?</w:pPr>|<w:pPr/>", p, re.S):
        return re.sub(r"<w:pPr>.*?</w:pPr>|<w:pPr/>", ppr, p, count=1, flags=re.S)
    return re.sub(r"^<w:p(\s[^>]*)?>", lambda m: m.group(0) + ppr, p, count=1)


def sect(cols, first=False):
    typ = "" if first else '<w:type w:val="continuous"/>'
    return (f'<w:sectPr>{typ}<w:pgSz w:w="{PAGE_W}" w:h="{PAGE_H}"/>'
            f'<w:pgMar w:top="{M_TOP}" w:right="{M_SIDE}" w:bottom="{M_BOTTOM}" w:left="{M_SIDE}" '
            f'w:header="720" w:footer="720" w:gutter="0"/><w:cols w:num="{cols}" w:space="{COL_GAP}"/></w:sectPr>')


def section_break(cols, first=False):
    """Empty paragraph that ends a section with `cols` columns."""
    return (f'<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="20" w:lineRule="exact"/>'
            f'<w:rPr><w:sz w:val="2"/></w:rPr>{sect(cols, first)}</w:pPr></w:p>')


def first_text_replace(p, pattern, repl):
    """Apply a regex to the text of the paragraph's first w:t only."""
    m = re.search(r'(<w:t(?:\s[^>]*)?>)([^<]*)(</w:t>)', p)
    if not m:
        return p
    new = re.sub(pattern, repl, m.group(2), count=1)
    return p[:m.start(2)] + new + p[m.end(2):]


def format_table(tbl, target):
    """Column widths from content, centred, compact cell margins, booktabs-like rules."""
    rows = re.findall(r"<w:tr[ >].*?</w:tr>", tbl, re.S)
    ncols = len(re.findall(r"<w:gridCol ", tbl))
    need = [0.0] * ncols
    for r in rows:
        c = 0
        for cell in re.findall(r"<w:tc>.*?</w:tc>", r, re.S):
            span = int((re.search(r'<w:gridSpan w:val="(\d+)"', cell) or [0, 1])[1])
            if span == 1 and c < ncols:
                need[c] = max(need[c], len(text_of(cell)))
            c += span
    width = [int(n * 88 + 150) for n in need]        # ~8 pt Times: 88 twips per character + margins
    if sum(width) > target:
        width = [int(w * target / sum(width)) for w in width]
    grid = "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}"/>' for w in width) + "</w:tblGrid>"
    tbl = re.sub(r"<w:tblGrid>.*?</w:tblGrid>", grid, tbl, flags=re.S)

    def cell_width(r):
        c, out = 0, []
        for cell in re.split(r"(<w:tc>.*?</w:tc>)", r, flags=re.S):
            if not cell.startswith("<w:tc>"):
                out.append(cell)
                continue
            span = int((re.search(r'<w:gridSpan w:val="(\d+)"', cell) or [0, 1])[1])
            w = sum(width[c:c + span])
            c += span
            tcw = f'<w:tcW w:w="{w}" w:type="dxa"/>'
            cell = cell.replace("<w:tcPr />", f"<w:tcPr>{tcw}</w:tcPr>", 1) if "<w:tcPr />" in cell \
                else cell.replace("<w:tcPr>", f"<w:tcPr>{tcw}", 1)
            out.append(cell)
        return "".join(out)
    tbl = re.sub(r"<w:tr[ >].*?</w:tr>", lambda m: cell_width(m.group(0)), tbl, flags=re.S)
    rows = re.findall(r"<w:tr[ >].*?</w:tr>", tbl, re.S)
    for r in rows[:-1]:
        tbl = tbl.replace(r, re.sub(r'(<w:pStyle w:val="Compact" ?/>)', r"\1<w:keepNext/>", r), 1)
    tblpr = (f'<w:tblPr><w:tblStyle w:val="Table"/><w:tblW w:w="{sum(width)}" w:type="dxa"/><w:jc w:val="center"/>'
             '<w:tblBorders><w:top w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
             '<w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
             '<w:insideH w:val="single" w:sz="2" w:space="0" w:color="BFBFBF"/></w:tblBorders>'
             '<w:tblLayout w:type="fixed"/>'
             '<w:tblCellMar><w:left w:w="57" w:type="dxa"/><w:right w:w="57" w:type="dxa"/></w:tblCellMar>'
             '<w:tblLook w:val="0020" w:firstRow="1" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" '
             'w:noHBand="0" w:noVBand="0"/></w:tblPr>')
    return re.sub(r"<w:tblPr>.*?</w:tblPr>", tblpr, tbl, count=1, flags=re.S)


def scale_drawing(p, width_in):
    m = re.search(r'<wp:extent cx="(\d+)" cy="(\d+)"', p)
    cx, cy = int(m.group(1)), int(m.group(2))
    ncx = int(width_in * EMU_PER_IN)
    ncy = int(cy * ncx / cx)
    return p.replace(f'cx="{cx}" cy="{cy}"', f'cx="{ncx}" cy="{ncy}"')


def ieee_document(doc):
    head, body, tail = re.match(r"(.*<w:body>)(.*)(</w:body>.*)", doc, re.S).groups()
    bl = blocks(body)
    out, eq, state = [], 0, "title"
    prev_equation = False
    i = 0
    while i < len(bl):
        b = bl[i]
        if b.startswith("<w:sectPr"):                  # pandoc's final section: replaced below
            i += 1
            continue
        if not b.startswith("<w:p") and not b.startswith("<w:tbl"):
            out.append(b)
            i += 1
            continue
        txt = text_of(b)
        sid = style_of(b) if b.startswith("<w:p") else ""

        if state == "title" and sid not in ("Title", "Author"):
            if txt.startswith("Abstract"):
                out.append(section_break(1, first=True))
                state = "body"
            else:
                out.append(set_style(b, "AuthorNote" if "contributed equally" in txt else "AuthorInfo"))
                i += 1
                continue
        if state == "title":
            out.append(b)
            i += 1
            continue

        if txt.startswith("Abstract") or txt.startswith("Index Terms"):
            out.append(set_style(b, "IEEEAbstract"))
        elif sid == "Heading1" and txt.strip() == "References":
            out.append(b)
            state = "refs"
        elif state == "refs" and re.match(r"\[\d+\] ", txt):
            p = first_text_replace(b, r"^(\[\d+\]) ", r'\1</w:t><w:tab/><w:t xml:space="preserve">')
            out.append(set_style(p, "Bibliography"))
        elif "<m:oMathPara" in b:                       # display equation: centre tab + number at right
            eq += 1
            math = re.search(r"<m:oMath>.*</m:oMath>", b, re.S).group(0)
            out.append(f'<w:p><w:pPr><w:pStyle w:val="Equation"/></w:pPr><w:r><w:tab/></w:r>{math}'
                       f'<w:r><w:tab/><w:t>({eq})</w:t></w:r></w:p>')
            prev_equation = True
            i += 1
            continue
        elif re.match(r"\d+\) ", txt) and sid in ("BodyText", "FirstParagraph"):
            p = first_text_replace(b, r"^(\d+\)) ", r'\1</w:t><w:tab/><w:t xml:space="preserve">')
            out.append(set_style(p, "ListNumbered"))
        elif prev_equation and sid in ("BodyText", "FirstParagraph") and txt[:1].islower():
            out.append(set_style(b, "BodyText", '<w:ind w:firstLine="0"/>'))
        elif sid == "TableCaption":
            label = re.match(r"(TABLE [IVX]+)\. ", txt).group(1)
            p = first_text_replace(b, r"^(TABLE [IVX]+)\. ", r'\1</w:t><w:br/><w:t xml:space="preserve">')
            tbl = bl[i + 1] if i + 1 < len(bl) and bl[i + 1].startswith("<w:tbl") else None
            j = i + 1
            while tbl is None and j < len(bl):         # whitespace between caption and table
                if bl[j].startswith("<w:tbl"):
                    tbl = bl[j]
                    break
                j += 1
            wide = label in WIDE
            block = [p, format_table(tbl, TEXT_W if wide else COL_W)]
            out += [section_break(2)] + block + [section_break(1)] if wide else block
            i = j + 1
            prev_equation = False
            continue
        elif sid == "CaptionedFigure":
            cap = next(x for x in bl[i + 1:] if x.startswith("<w:p"))
            capidx = bl.index(cap, i + 1)
            label = re.match(r"Fig\.\s*(\d+)\.", text_of(cap))
            wide = label and f"Fig. {label.group(1)}" in WIDE
            fig = scale_drawing(b, 7.0) if wide else b
            block = [fig, cap]
            out += [section_break(2)] + block + [section_break(1)] if wide else block
            i = capidx + 1
            prev_equation = False
            continue
        else:
            out.append(b)
        prev_equation = False
        i += 1
    return head + "".join(out) + sect(2) + tail


# ---------------------------------------------------------------- styles
def pstyle(sid, name, ppr="", rpr="", based="Normal", nxt=None):
    nx = f'<w:next w:val="{nxt}"/>' if nxt else ""
    return (f'<w:style w:type="paragraph" w:customStyle="1" w:styleId="{sid}"><w:name w:val="{name}"/>'
            f'<w:basedOn w:val="{based}"/>{nx}<w:qFormat/><w:pPr>{ppr}</w:pPr><w:rPr>{rpr}</w:rPr></w:style>')


def ieee_styles(st):
    st = re.sub(r'w:(ascii|hAnsi|eastAsia|cs)Theme="[^"]*"', "", st)
    st = re.sub(r"<w:rFonts[^>]*/>", f"<w:rFonts {TNR}/>", st)
    st = re.sub(r'<w:color w:val="[0-9A-Fa-f]{6}"[^>]*/>', '<w:color w:val="000000"/>', st)
    st = re.sub(r"(<w:rPrDefault>.*?)<w:sz w:val=\"\d+\"\s*/>", r'\1<w:sz w:val="20"/>', st, flags=re.S)
    tab_eq = (f'<w:tabs><w:tab w:val="center" w:pos="{COL_W // 2}"/><w:tab w:val="right" w:pos="{COL_W}"/></w:tabs>')
    body = '<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/><w:ind w:firstLine="288"/><w:jc w:val="both"/>'
    new = {
        "Normal": ('<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/>'
                   '<w:pPr><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
                   f'<w:rPr><w:rFonts {TNR}/><w:sz w:val="20"/><w:szCs w:val="20"/><w:lang w:val="en-US"/></w:rPr></w:style>'),
        "BodyText": pstyle("BodyText", "Body Text", body),
        "FirstParagraph": pstyle("FirstParagraph", "First Paragraph", body, based="BodyText", nxt="BodyText"),
        "Compact": pstyle("Compact", "Table Text", '<w:spacing w:before="0" w:after="0"/><w:ind w:firstLine="0"/>',
                          '<w:sz w:val="16"/><w:szCs w:val="16"/>'),
        "Title": pstyle("Title", "Title", '<w:spacing w:before="0" w:after="120"/><w:jc w:val="center"/>',
                        '<w:kern w:val="28"/><w:sz w:val="48"/><w:szCs w:val="48"/>'),
        "Author": pstyle("Author", "Author", '<w:spacing w:before="120" w:after="40"/><w:jc w:val="center"/>',
                         '<w:sz w:val="22"/><w:szCs w:val="22"/>'),
        "AuthorInfo": pstyle("AuthorInfo", "Author Affiliation", '<w:spacing w:before="0" w:after="0"/><w:jc w:val="center"/>',
                             '<w:sz w:val="20"/><w:szCs w:val="20"/>'),
        "AuthorNote": pstyle("AuthorNote", "Author Note", '<w:spacing w:before="60" w:after="160"/><w:jc w:val="center"/>',
                             '<w:sz w:val="16"/><w:szCs w:val="16"/>'),
        "IEEEAbstract": pstyle("IEEEAbstract", "Abstract",
                               '<w:spacing w:before="0" w:after="120"/><w:ind w:firstLine="202"/><w:jc w:val="both"/>',
                               '<w:b/><w:bCs/><w:sz w:val="18"/><w:szCs w:val="18"/>'),
        "Heading1": pstyle("Heading1", "heading 1", '<w:keepNext/><w:keepLines/><w:spacing w:before="160" w:after="80"/>'
                           '<w:jc w:val="center"/><w:outlineLvl w:val="0"/>',
                           '<w:smallCaps/><w:sz w:val="20"/><w:szCs w:val="20"/>', nxt="BodyText"),
        "Heading2": pstyle("Heading2", "heading 2", '<w:keepNext/><w:keepLines/><w:spacing w:before="80" w:after="40"/>'
                           '<w:outlineLvl w:val="1"/>', '<w:i/><w:iCs/><w:sz w:val="20"/><w:szCs w:val="20"/>', nxt="BodyText"),
        "Equation": pstyle("Equation", "Equation", f'{tab_eq}<w:spacing w:before="60" w:after="60"/>'),
        "ListNumbered": pstyle("ListNumbered", "List (IEEE)",
                               '<w:tabs><w:tab w:val="left" w:pos="288"/></w:tabs><w:spacing w:before="0" w:after="0"/>'
                               '<w:ind w:left="288" w:hanging="288"/><w:jc w:val="both"/>'),
        "TableCaption": pstyle("TableCaption", "Table Title", '<w:keepNext/><w:spacing w:before="160" w:after="80"/><w:jc w:val="center"/>',
                               '<w:smallCaps/><w:sz w:val="16"/><w:szCs w:val="16"/>'),
        "ImageCaption": pstyle("ImageCaption", "Figure Caption", '<w:spacing w:before="40" w:after="160"/><w:jc w:val="both"/>',
                               '<w:sz w:val="16"/><w:szCs w:val="16"/>'),
        "CaptionedFigure": pstyle("CaptionedFigure", "Captioned Figure", '<w:keepNext/><w:spacing w:before="160" w:after="0"/><w:jc w:val="center"/>'),
        "Bibliography": pstyle("Bibliography", "Reference",
                               '<w:tabs><w:tab w:val="left" w:pos="360"/></w:tabs><w:spacing w:before="0" w:after="0"/>'
                               '<w:ind w:left="360" w:hanging="360"/><w:jc w:val="both"/>', '<w:sz w:val="16"/><w:szCs w:val="16"/>'),
    }
    for sid, xml in new.items():
        st = re.sub(rf'<w:style [^>]*w:styleId="{sid}"[^>]*>.*?</w:style>', "", st, flags=re.S)
        st = st.replace("</w:styles>", xml + "</w:styles>")
    return st


def build_docx(raw, dst):
    with zipfile.ZipFile(raw) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename.endswith("/"):
                continue
            data = zin.read(item.filename)
            if item.filename == "word/styles.xml":
                data = ieee_styles(data.decode("utf-8")).encode("utf-8")
            elif item.filename == "word/document.xml":
                data = ieee_document(data.decode("utf-8")).encode("utf-8")
            elif item.filename == "[Content_Types].xml":
                s = data.decode("utf-8")
                if 'Extension="png"' not in s:
                    s = s.replace('<Default Extension="xml"', '<Default Extension="png" ContentType="image/png" /><Default Extension="xml"', 1)
                data = s.encode("utf-8")
            zout.writestr(item, data)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        for f in ["main.tex", "refs.bib", *[p.name for p in HERE.glob("tab_*.tex")], *[p.name for p in HERE.glob("fig_*.pdf")]]:
            shutil.copy(HERE / f, tmp)
        run(["tectonic", "-X", "compile", "--keep-intermediates", "main.tex"], tmp)
        (tmp / "docx_source.tex").write_text(prepare_source(tmp))
        run(["pandoc", "docx_source.tex", "-f", "latex", "-t", "docx", "-o", "raw.docx"], tmp)
        build_docx(tmp / "raw.docx", OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
