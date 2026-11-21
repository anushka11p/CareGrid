"""Build an editable Word version of the paper: paper_team/CareGrid_paper.docx.

Steps: compile main.tex once (tectonic, keeping main.aux and main.bbl) to get the citation and
figure/table numbers; render the TikZ shield diagram to PNG; rewrite main.tex into plain LaTeX
that pandoc reads well (numbers filled in, tables inlined, PNG figures, reference list from the
.bbl); run pandoc; restyle the Word file (Times New Roman, black headings, table borders).
Needs tectonic, pdftoppm and pandoc on PATH. Run from anywhere:
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


def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def cite_text(nums):
    """IEEE style: [1], [3]-[5]."""
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
        text = text.replace("\\newblock", "").replace("\n", " ")
        text = re.sub(r"\s+", " ", text).strip()
        lines.append((bibnum[key], text))
    return sorted(lines)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        for f in ["main.tex", "refs.bib", *map(str, HERE.glob("tab_*.tex")), *map(str, HERE.glob("fig_*.pdf"))]:
            shutil.copy(HERE / pathlib.Path(f).name, tmp)
        run(["tectonic", "-X", "compile", "--keep-intermediates", "main.tex"], tmp)
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
        src = src.replace(tikz, "\\includegraphics[width=\\columnwidth]{fig_shield.png}")
        for f in (HERE / "figures").glob("fig_*.png"):
            shutil.copy(f, tmp)
        src = re.sub(r"\{(fig_[a-z]+)\.pdf\}", r"{\1.png}", src)
        widths = {"shield": "3.6in", "duration": "4.3in", "case": "6.5in", "forecast": "5.2in", "learning": "5.2in"}
        src = re.sub(r"\\includegraphics\[[^\]]*\]\{fig_([a-z]+)\.png\}",
                     lambda m: f"\\includegraphics[width={widths[m.group(1)]}]{{fig_{m.group(1)}.png}}", src)

        # tables inline, single column, no layout-only commands
        for t in re.findall(r"\\input\{(tab_[a-z]+)\.tex\}", src):
            body = (tmp / f"{t}.tex").read_text()
            body = body.replace("table*", "table").replace("\\quad ", "-- ")
            body = re.sub(r"\\setlength\{[^}]*\}\{[^}]*\}|\\footnotesize|\\cmidrule\([^)]*\)\{[^}]*\}", "", body)
            src = src.replace(f"\\input{{{t}.tex}}", body)
        src = src.replace("\\begin{figure*}", "\\begin{figure}").replace("\\end{figure*}", "\\end{figure}")

        # numbered captions (Word file has no automatic numbering here)
        def number_caption(m):
            env, caption, label = m.group(1), m.group(2), m.group(3)
            n = labels[label]
            prefix = f"Fig.~{n}. " if env == "figure" else f"TABLE {n}. "
            return m.group(0).replace(f"\\caption{{{caption}}}", f"\\caption{{{prefix}{caption}}}", 1)
        src = re.sub(r"\\begin\{(figure|table)\}.*?\\caption\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}\s*\\label\{([^}]*)\}.*?\\end\{\1\}",
                     number_caption, src, flags=re.S)
        src = re.sub(r"\\ref\{([^}]*)\}", lambda m: labels[m.group(1)], src)
        src = re.sub(r"\\label\{[^}]*\}", "", src)
        src = re.sub(r"\\cite\{([^}]*)\}", lambda m: cite_text(bibnum[k.strip()] for k in m.group(1).split(",")), src)

        # title block
        thanks = re.search(r"\\thanks\{(.*?)\}\}\s*\n\s*\\maketitle", src, re.S).group(1)
        thanks = thanks.replace("$^{\\dagger}$", "†").replace("$^{*}$", "*")
        author = re.search(r"\\author\{.*?\\maketitle", src, re.S).group(0)
        src = src.replace(author, (
            "\\author{Khrisha N\\textsuperscript{1,†}, Anushka Prasad\\textsuperscript{1,†}, "
            "Pushpa Mitra Ganesh\\textsuperscript{1,†} and P. Madhavan\\textsuperscript{2,*}}\n\\maketitle\n\n"
            "\\textsuperscript{1}Department of Electronics and Computer Engineering; "
            "\\textsuperscript{2}Department of Computing Technologies. Faculty of Engineering and Technology, "
            "SRM Institute of Science and Technology, Kattankulathur, Chennai, India. "
            "\\{kn9023, ap0362, pg5197, madhavap\\}@srmist.edu.in\n\n" + thanks + "\n"))
        src = re.sub(r"\\begin\{abstract\}(.*?)\\end\{abstract\}",
                     lambda m: "\\noindent\\textbf{\\textit{Abstract}}---" + m.group(1).strip(), src, flags=re.S)

        def manual_numbers(m):                      # Word restarts list numbering after a display equation
            items = re.split(r"\\item\s+", m.group(1))[1:]
            return "\n\n" + "\n\n".join(f"{i}) {it.strip()}" for i, it in enumerate(items, 1)) + "\n\n"
        src = re.sub(r"\\begin\{enumerate\}((?:(?!\\end\{enumerate\}).)*?\\begin\{equation\}.*?)\\end\{enumerate\}",
                     manual_numbers, src, flags=re.S)
        src = re.sub(r"\\begin\{IEEEkeywords\}(.*?)\\end\{IEEEkeywords\}",
                     lambda m: "\\textbf{Index Terms}---" + m.group(1).strip(), src, flags=re.S)
        src = re.sub(r"\\bstctlcite\{[^}]*\}|\\IEEEoverridecommandlockouts", "", src)
        src = src.replace("\\documentclass[conference]{IEEEtran}", "\\documentclass{article}")

        # references from the .bbl
        refs = bbl_items((tmp / "main.bbl").read_text(), bibnum)
        src = re.sub(r"\\bibliographystyle\{[^}]*\}\s*\\bibliography\{[^}]*\}",
                     lambda m: "\\section*{References}\n\n" + "\n\n".join(f"[{n}] {t}" for n, t in refs), src)
        (tmp / "docx_source.tex").write_text(src)

        run(["pandoc", "docx_source.tex", "-f", "latex", "-t", "docx", "-o", "raw.docx"], tmp)
        restyle(tmp / "raw.docx", OUT)
    print(f"wrote {OUT}")


def restyle(src, dst):
    """Times New Roman throughout, black headings, borders on tables."""
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename.endswith("/"):
                continue
            data = zin.read(item.filename)
            if item.filename == "word/styles.xml":
                s = data.decode("utf-8")
                s = re.sub(r'w:(ascii|hAnsi|eastAsia|cs)Theme="[^"]*"', "", s)
                s = re.sub(r"<w:rFonts[^>]*/>", '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
                           'w:eastAsia="Times New Roman" w:cs="Times New Roman"/>', s)
                s = re.sub(r'<w:color w:val="[0-9A-Fa-f]{6}"[^>]*/>', '<w:color w:val="000000"/>', s)
                data = s.encode("utf-8")
            if item.filename == "[Content_Types].xml":
                s = data.decode("utf-8")
                if 'Extension="png"' not in s:
                    s = s.replace('<Default Extension="xml"', '<Default Extension="png" ContentType="image/png" /><Default Extension="xml"', 1)
                data = s.encode("utf-8")
            if item.filename == "word/document.xml":
                s = data.decode("utf-8")
                borders = ('<w:tblBorders><w:top w:val="single" w:sz="8" w:color="000000"/>'
                           '<w:bottom w:val="single" w:sz="8" w:color="000000"/>'
                           '<w:insideH w:val="single" w:sz="2" w:color="BFBFBF"/></w:tblBorders>')
                # schema order: tblBorders comes before shd, tblLayout, tblCellMar and tblLook
                def centre(m):
                    para = m.group(0)
                    if "Department of Electronics" not in para and "contributed equally" not in para:
                        return para
                    if "<w:pPr>" in para:
                        return para.replace("<w:pPr>", '<w:pPr><w:jc w:val="center"/>', 1) if "<w:pStyle" not in para \
                            else re.sub(r"(<w:pStyle [^>]*/>)", r'\1<w:jc w:val="center"/>', para, count=1)
                    return para.replace("<w:p>", '<w:p><w:pPr><w:jc w:val="center"/></w:pPr>', 1)
                s = re.sub(r"<w:p>(?:(?!</w:p>).)*</w:p>", centre, s, flags=re.S)
                s = re.sub(r"(<w:tblPr>(?:(?!</w:tblPr>).)*?)(<w:shd|<w:tblLayout|<w:tblCellMar|<w:tblLook|</w:tblPr>)",
                           lambda m: m.group(1) + borders + m.group(2), s, flags=re.S)
                data = s.encode("utf-8")
            zout.writestr(item, data)


if __name__ == "__main__":
    main()
