"""
omml_equations.py -- build the manuscript display equations as native Office Math
(OMML) fragments, so they are real Word equations (editable in the Equation tab),
not images. Each entry maps a marker name to the inner XML of an <m:oMath> element.

Used by build_docx.py via parse_xml(oMath(name)).
"""

M = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def _esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def r(text, plain=False):
    """A math run. plain=True -> upright (function names, units, multi-letter subs)."""
    rpr = '<m:rPr><m:sty m:val="p"/></m:rPr>' if plain else ""
    return f'<m:r>{rpr}<m:t xml:space="preserve">{_esc(text)}</m:t></m:r>'


def fn(name):       # upright function / operator name
    return r(name, plain=True)


def sub(base, s):
    return f"<m:sSub><m:e>{base}</m:e><m:sub>{s}</m:sub></m:sSub>"


def sup(base, s):
    return f"<m:sSup><m:e>{base}</m:e><m:sup>{s}</m:sup></m:sSup>"


def subsup(base, s, p):
    return (f"<m:sSubSup><m:e>{base}</m:e><m:sub>{s}</m:sub>"
            f"<m:sup>{p}</m:sup></m:sSubSup>")


def frac(num, den):
    return f"<m:f><m:num>{num}</m:num><m:den>{den}</m:den></m:f>"


def rad(e):         # square root
    return ('<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr>'
            f"<m:deg/><m:e>{e}</m:e></m:rad>")


def dl(e, beg="(", end=")"):
    return ('<m:d><m:dPr>'
            f'<m:begChr m:val="{beg}"/><m:endChr m:val="{end}"/></m:dPr>'
            f"<m:e>{e}</m:e></m:d>")


# --- equation content (inner XML of <m:oMath>) ----------------------------- #
def _windspeed():
    return (sub(r("U"), r("10")) + r(" = ")
            + rad(subsup(r("u"), r("10"), r("2")) + r(" + ")
                  + subsup(r("v"), r("10"), r("2"))))


def _winddir():
    inner = (r("−") + sub(r("u"), r("10")) + r(", −") + sub(r("v"), r("10")))
    return (sub(r("θ"), r("w", plain=True)) + r(" = ")
            + dl(frac(r("180"), r("π")) + fn("atan2") + dl(inner),
                 "[", "]")
            + r("  ") + fn("mod") + r(" 360°"))


def _magnus():
    num1 = r("a ") + sub(r("T"), r("d", plain=True))
    den1 = r("b + ") + sub(r("T"), r("d", plain=True))
    num2 = r("a ") + sub(r("T"), r("a", plain=True))
    den2 = r("b + ") + sub(r("T"), r("a", plain=True))
    bracket = frac(num1, den1) + r(" − ") + frac(num2, den2)
    return (r("RH", plain=True) + r(" = 100 ") + fn("exp") + dl(bracket, "[", "]")
            + r(",   a = 17.625,   b = 243.04"))


def _sigmaz():
    return (sub(r("z"), r("k")) + r(" = ζ + ") + sub(r("σ"), r("k"))
            + dl(r("ζ + d")) + r(",   ") + sub(r("σ"), r("k"))
            + r(" ∈ [0, −1]"))


def _rotation():
    p1 = (sub(r("u"), r("E", plain=True)) + r(" = ")
          + sub(r("u"), r("ξ")) + fn("cos") + r("α − ")
          + sub(r("v"), r("η")) + fn("sin") + r("α"))
    p2 = (sub(r("v"), r("N", plain=True)) + r(" = ")
          + sub(r("u"), r("ξ")) + fn("sin") + r("α + ")
          + sub(r("v"), r("η")) + fn("cos") + r("α"))
    return p1 + r("  ") + p2


def _stokes():
    return (r("ω = ") + frac(r("2π"), sub(r("T"), r("p", plain=True)))
            + r(",   k = ") + frac(sup(r("ω"), r("2")), r("g"))
            + r(",   a = ") + frac(sub(r("H"), r("s", plain=True)),
                                   r("2") + rad(r("2")))
            + r(",   |") + sub(r("U"), r("s", plain=True)) + r("| = ω k ")
            + sup(r("a"), r("2")))


def _radius():
    inner = (sub(r("r"), r("max", plain=True)) + r(", 0.6 ")
             + sub(r("D"), r("shore", plain=True)))
    return (r("r = ") + fn("min") + dl(inner)
            + r(",   ") + sub(r("D"), r("shore", plain=True)) + r(" = ")
            + fn("max") + r(" EDT") + dl(r("wet mask")))


def _drift():
    t1 = (dl(sub(r("λ"), r("i")) + r(" − ") + sub(r("λ"), r("0")))
          + fn("cos") + r("φ ") + sub(r("R"), r("e", plain=True)))
    t2 = (dl(sub(r("φ"), r("i")) + r(" − ") + sub(r("φ"), r("0")))
          + r(" ") + sub(r("R"), r("e", plain=True)))
    body = sup(dl(t1, "[", "]"), r("2")) + r(" + ") + sup(dl(t2, "[", "]"), r("2"))
    return (sub(r("D"), r("i")) + r(" = ") + rad(body)
            + r(",   ") + sub(r("R"), r("e", plain=True))
            + r(" ≈ 111 km/deg"))


EQUATIONS = {
    "windspeed": _windspeed(), "winddir": _winddir(), "magnus": _magnus(),
    "sigmaz": _sigmaz(), "rotation": _rotation(), "stokes": _stokes(),
    "radius": _radius(), "drift": _drift(),
}
EQ_NUM = {"windspeed": 1, "winddir": 2, "magnus": 3, "sigmaz": 4,
          "rotation": 5, "stokes": 6, "radius": 7, "drift": 8}


def oMath(name):
    """Full <m:oMath> element XML (namespace-declared) for parse_xml()."""
    return f'<m:oMath xmlns:m="{M}">{EQUATIONS[name]}</m:oMath>'


if __name__ == "__main__":
    for k in EQUATIONS:
        x = oMath(k)
        # quick well-formedness check
        from xml.dom.minidom import parseString
        parseString(x)
        print(f"{k:10s} OK  ({len(x)} chars)")
