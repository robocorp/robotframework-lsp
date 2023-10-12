"use strict";
var U = Object.defineProperty,
    F = Object.defineProperties;
var G = Object.getOwnPropertyDescriptors;
var I = Object.getOwnPropertySymbols;
var Y = Object.prototype.hasOwnProperty,
    j = Object.prototype.propertyIsEnumerable;
var X = (i, r, e) => (r in i ? U(i, r, { enumerable: !0, configurable: !0, writable: !0, value: e }) : (i[r] = e)),
    p = (i, r) => {
        for (var e in r || (r = {})) Y.call(r, e) && X(i, e, r[e]);
        if (I) for (var e of I(r)) j.call(r, e) && X(i, e, r[e]);
        return i;
    },
    y = (i, r) => F(i, G(r));
var b = (i, r, e) =>
    new Promise((n, t) => {
        var s = (c) => {
                try {
                    a(e.next(c));
                } catch (u) {
                    t(u);
                }
            },
            o = (c) => {
                try {
                    a(e.throw(c));
                } catch (u) {
                    t(u);
                }
            },
            a = (c) => (c.done ? n(c.value) : Promise.resolve(c.value).then(s, o));
        a((e = e.apply(i, r)).next());
    });
let h, S;
function z(i, r) {
    if (i.nodeType !== Node.ELEMENT_NODE) throw new Error("Can't generate CSS selector for non-element node type.");
    if (i.tagName.toLowerCase() === "html") return "html";
    const e = {
        root: document.body,
        idName: (t) => !0,
        className: (t) => !0,
        tagName: (t) => !0,
        attr: (t, s) => !1,
        seedMinLength: 1,
        optimizedMinLength: 2,
        threshold: 1e3,
        maxNumberOfTries: 1e4,
    };
    (h = p(p({}, e), r)), (S = K(h.root, e));
    let n = k(i, "all", () => k(i, "two", () => k(i, "one", () => k(i, "none"))));
    if (n) {
        const t = V(M(n, i));
        return t.length > 0 && (n = t[0]), L(n);
    } else throw new Error("Selector was not found.");
}
function K(i, r) {
    return i.nodeType === Node.DOCUMENT_NODE ? i : i === r.root ? i.ownerDocument : i;
}
function k(i, r, e) {
    let n = null,
        t = [],
        s = i,
        o = 0;
    for (; s; ) {
        let a = N(W(s)) || N(...J(s)) || N(...Q(s)) || N(Z(s)) || [R()];
        const c = ee(s);
        if (r == "all") c && (a = a.concat(a.filter(w).map((u) => P(u, c))));
        else if (r == "two") (a = a.slice(0, 1)), c && (a = a.concat(a.filter(w).map((u) => P(u, c))));
        else if (r == "one") {
            const [u] = (a = a.slice(0, 1));
            c && w(u) && (a = [P(u, c)]);
        } else r == "none" && ((a = [R()]), c && (a = [P(a[0], c)]));
        for (let u of a) u.level = o;
        if ((t.push(a), t.length >= h.seedMinLength && ((n = T(t, e)), n))) break;
        (s = s.parentElement), o++;
    }
    return n || (n = T(t, e)), !n && e ? e() : n;
}
function T(i, r) {
    const e = V(O(i));
    if (e.length > h.threshold) return r ? r() : null;
    for (let n of e) if (D(n)) return n;
    return null;
}
function L(i) {
    let r = i[0],
        e = r.name;
    for (let n = 1; n < i.length; n++) {
        const t = i[n].level || 0;
        r.level === t - 1 ? (e = `${i[n].name} > ${e}`) : (e = `${i[n].name} ${e}`), (r = i[n]);
    }
    return e;
}
function A(i) {
    return i.map((r) => r.penalty).reduce((r, e) => r + e, 0);
}
function D(i) {
    const r = L(i);
    switch (S.querySelectorAll(r).length) {
        case 0:
            throw new Error(`Can't select any node with this selector: ${r}`);
        case 1:
            return !0;
        default:
            return !1;
    }
}
function W(i) {
    const r = i.getAttribute("id");
    return r && h.idName(r) ? { name: "#" + CSS.escape(r), penalty: 0 } : null;
}
function J(i) {
    return Array.from(i.attributes)
        .filter((e) => h.attr(e.name, e.value))
        .map((e) => ({ name: `[${CSS.escape(e.name)}="${CSS.escape(e.value)}"]`, penalty: 0.5 }));
}
function Q(i) {
    return Array.from(i.classList)
        .filter(h.className)
        .map((e) => ({ name: "." + CSS.escape(e), penalty: 1 }));
}
function Z(i) {
    const r = i.tagName.toLowerCase();
    return h.tagName(r) ? { name: r, penalty: 2 } : null;
}
function R() {
    return { name: "*", penalty: 3 };
}
function ee(i) {
    const r = i.parentNode;
    if (!r) return null;
    let e = r.firstChild;
    if (!e) return null;
    let n = 0;
    for (; e && (e.nodeType === Node.ELEMENT_NODE && n++, e !== i); ) e = e.nextSibling;
    return n;
}
function P(i, r) {
    return { name: i.name + `:nth-child(${r})`, penalty: i.penalty + 1 };
}
function w(i) {
    return i.name !== "html" && !i.name.startsWith("#");
}
function N(...i) {
    const r = i.filter(te);
    return r.length > 0 ? r : null;
}
function te(i) {
    return i != null;
}
function* O(i, r = []) {
    if (i.length > 0) for (let e of i[0]) yield* O(i.slice(1, i.length), r.concat(e));
    else yield r;
}
function V(i) {
    return [...i].sort((r, e) => A(r) - A(e));
}
function* M(i, r, e = { counter: 0, visited: new Map() }) {
    if (i.length > 2 && i.length > h.optimizedMinLength)
        for (let n = 1; n < i.length - 1; n++) {
            if (e.counter > h.maxNumberOfTries) return;
            e.counter += 1;
            const t = [...i];
            t.splice(n, 1);
            const s = L(t);
            if (e.visited.has(s)) return;
            D(t) && ne(t, r) && (yield t, e.visited.set(s, !0), yield* M(t, r, e));
        }
}
function ne(i, r) {
    return S.querySelector(L(i)) === r;
}
const ie = ["name", "title", "id", "for", "href", "class"],
    l = { info: console.log, debug: console.debug, error: console.error },
    re = () => new Date().getTime(),
    se = (i) => i.nodeType === Node.ELEMENT_NODE,
    C = (i) => ["text", "file", "select"].includes(i),
    B = (i) => {
        const r = i.tagName.toLowerCase();
        if ((l.debug("[elementClassifier] Classify tag:", r), r === "input")) {
            const e = i;
            switch ((l.debug("[elementClassifier] Element from input:", e), e.type)) {
                case "password":
                    return { type: "text", value: e.value };
                case "radio":
                    return { type: "radio", value: e.value };
                case "checkbox":
                    return { type: "checkbox", value: e.checked };
                case "file":
                    return { type: "file", value: e.value };
                case "email":
                case "tel":
                case "url":
                case "number":
                case "search":
                case "text":
                case "time":
                case "date":
                case "datetime-local":
                case "week":
                case "month":
                case "color":
                    return { type: "text", value: e.value };
                case "submit":
                case "image":
                case "range":
                case "reset":
                    return { type: e.type, value: void 0 };
            }
        } else if (r === "textarea") {
            const e = i;
            return l.debug("[elementClassifier] Element from textarea:", e), { type: "text", value: e.value };
        } else if (r === "select") {
            const e = i;
            return l.debug("[elementClassifier] Element from select:", e), { type: "select", value: e.value };
        } else if (r === "a") {
            const e = i;
            return l.debug("[classifyRawElement] Element from a:", e), { type: "a", value: e.href };
        } else if (r === "button") {
            const e = i;
            return l.debug("[elementClassifier] Element from button:", e), { type: "button", value: e.value };
        } else if (typeof i.onclick == "function" || typeof i.onmousedown == "function") {
            l.debug("[elementClassifier] Element from unknown element with onClick function:", i); //! TODO: This might need replacement with a better object
            return { type: "reset", value: void 0 };
        }
        l.debug("[elementClassifier] ERROR - Element could not be classified");
    },
    oe = {
        parseNode(i, r, e, n) {
            if (
                (l.debug("Parsing Node:", i, "selectors:", r, "attributesArray:", e, "forceClassified:", n),
                i !== void 0)
            ) {
                l.debug("[scanner.parseNode] Creating hash...");
                let t = n || B(i);
                t === void 0 && i.parentElement && ((t = B(i.parentElement)), (i = i.parentElement)),
                    l.debug("[scanner.parseNode] Hash:", t);
                const s = le.build(i, e, []);
                l.debug("[scanner.parseNode] Tree:", s);
                const o = re();
                if (t !== void 0) {
                    const a = ae.build(s, i, t.type || "default");
                    l.debug("[scanner.parseNode] Built path:", a);
                    const c = y(p({}, t), { selectors: r, time: o, path: a });
                    return l.debug("[scanner.parseNode] Parsed Node:", c), c;
                }
                l.error("[scanner.parseNode] Parsing failed. No Hash!");
                return;
            }
            l.error("[scanner.parseNode] Parsing failed. No Node!");
        },
    },
    x = (i, r, e) => {
        try {
            l.debug("[classifyEvent] Classifying event:", i);
            const n = i.target;
            if (!(n instanceof HTMLElement || n instanceof SVGElement)) {
                l.debug("Element not HTMLElement:", n);
                return;
            }
            const t = r.build(n).map((o) => r.getSelectorAsObject(o));
            if ((l.debug("[classifyEvent] Selectors (mapped) from builder:", t), t.length === 0)) {
                l.debug("[classifyEvent] Skipping committing due to no selectors");
                return;
            }
            const s = oe.parseNode(n, t, ie, e);
            if ((l.debug("[classifyEvent] Element attributes:", s), !s)) {
                l.debug("[classifyEvent] Skipping committing due to no relevant attributes");
                return;
            }
            return s.type === "text" && s.value === ""
                ? (l.debug("[classifyEvent] Skipping saving empty text event"),
                  { selectors: [], node: void 0, skipError: !0 })
                : { selectors: t, node: s };
        } catch (n) {
            l.error("[classifyEvent] Could not classify event due to error:", n);
            return;
        }
    },
    le = {
        _getIndex(i) {
            let r = !1,
                e = 0,
                n = 0;
            if (!i.parentNode) return 0;
            const t = i.parentNode.childNodes;
            for (let s = 0; s < t.length; s++) {
                t[s] === i && (r = !0);
                const o = t[s];
                se(o) && o.tagName === i.tagName && ((e += 1), (n = r ? n : n + 1));
            }
            return e > 1 ? n + 1 : 0;
        },
        _buildAttributes(i, r) {
            return r
                .map((n) => {
                    let t;
                    return (
                        n === "className"
                            ? (t = i.className.length > 0 ? i.className.split(" ") : null)
                            : n === "index"
                            ? (t = 1)
                            : (t = i.getAttribute(n)),
                        t ? { [`${n}`]: t } : null
                    );
                })
                .filter((n) => n);
        },
        build(i, r, e) {
            if (
                (l.debug("[builder.build] Building for element:", i, "with attributes:", r, "and pathList:", e),
                !i || !i.parentNode || i.nodeType === Node.DOCUMENT_NODE)
            )
                return e;
            const n = this._buildAttributes(i, r);
            return e.push({ [`${i.tagName.toLowerCase()}`]: n }), this.build(i.parentNode, r, e);
        },
    },
    ae = {
        build(i, r, e) {
            const n = i[0],
                t = Object.keys(n)[0],
                s = n[t].reduce((u, d) => (u === "" ? this._getSubpath(u, d, t) : u), ""),
                o = `/${s}`;
            if (
                (l.debug("[locator.build] Building for Item:", n, "tag:", t, "p:", s, "path:", o),
                !r ||
                    this._found(["@id", "@for"], o) ||
                    (this._found(["@name"], o) && this._found(["select"], e)) ||
                    o === "/")
            )
                return o;
            const { count: a, index: c } = this._getIndex(o, r);
            return a > 1 && c > 1 ? `xpath=(${o})[${c}]` : o;
        },
        _found(i, r) {
            return i.some((e) => r.includes(e));
        },
        _getIndex(i, r) {
            let e = 1,
                n = 1,
                t;
            const s = document.evaluate(`.${i}`, document.body, null, XPathResult.ORDERED_NODE_ITERATOR_TYPE, null);
            for (; t === s.iterateNext(); ) t === r && (e = n), (n += 1);
            return { count: n, index: e };
        },
        _getSubpath(i, r, e) {
            return r.for != null
                ? `/${e}[@for="${r.for}"]`
                : r.class != null && typeof r.class != "number" && r.class.length > 0
                ? `/${e}[@class="${r.class}"]`
                : r.title != null
                ? `/${e}[@title="${r.title}"]`
                : r.href != null
                ? `/${e}[@href="${r.href}"]`
                : r.name != null
                ? `/${e}[@name="${r.name}"]`
                : r.id != null
                ? `/${e}[@id="${r.id}"]`
                : r.index != null
                ? `/${e}`
                : "";
        },
    },
    m = {
        isElement: (i) => i.nodeType === window.Node.ELEMENT_NODE,
        isImage: (i) => i.nodeName.toUpperCase() === "IMG",
        isLink: (i) => i.nodeName.toUpperCase() === "A",
        isInput: (i) => i.nodeName.toUpperCase() === "INPUT",
        isLabel: (i) => i.nodeName.toUpperCase() === "LABEL",
    };
class ce {
    constructor(r) {
        (this.build = (e) => {
            l.debug("[builder] Building for Element:", e);
            const n = [
                    ["css:attributes", this.buildCssDataAttr],
                    ["id", this.buildId],
                    ["link", this.buildLinkText],
                    ["name", this.buildName],
                    ["css", this.buildCssFinder],
                    ["xpath:link-text", this.buildXPathLink],
                    ["xpath:image", this.buildXPathImg],
                    ["xpath:attributes", this.buildXPathAttr],
                    ["xpath:relative-id", this.buildXPathIdRelative],
                    ["xpath:href", this.buildXPathHref],
                    ["xpath:position", this.buildXPathPosition],
                    ["xpath:inner-text", this.buildXPathInnerText],
                    ["xpath:input-label", this.buildXPathInputLabel],
                ],
                t = [];
            return (
                n.forEach(([s, o]) => {
                    try {
                        const a = o(e);
                        a && (typeof a == "string" ? t.push([s, a]) : a.forEach((c) => t.push([s, c])));
                    } catch (a) {
                        l.error(`[builder] Failed to build '${s}': ${a}`);
                    }
                }),
                t
            );
        }),
            (this.logValidation = (e, n) => (
                e
                    ? l.debug("[builder] Selector validation PASSED for:", n)
                    : l.debug("[builder] Selector validation FAILED for:", n),
                e
            )),
            (this.validateId = (e) => document.getElementById(e) !== null),
            (this.validateName = (e) => document.getElementsByName(e) !== null),
            (this.validateXPath = (e) => document.evaluate(e, document, null, XPathResult.ANY_TYPE, null) !== null),
            (this.validateCSS = (e) => document.querySelector(e) !== null),
            (this.getSelectorAsObject = (e) => ({ strategy: e[0].split(":", 1)[0], value: e[1] })),
            (this.getElementByXPath = (e) =>
                document.evaluate(e, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue),
            (this.getXPathFromParent = (e) => {
                let n = "/" + e.nodeName.toLowerCase();
                const t = this.getNodeNumber(e);
                return t > 0 && (n += "[" + (t + 1) + "]"), n;
            }),
            (this.getNodeNumber = (e) => {
                var s;
                const n = ((s = e.parentNode) == null ? void 0 : s.childNodes) || [];
                let t = 0;
                for (let o = 0; o < n.length; o++) {
                    const a = n[o];
                    if (a.nodeName === e.nodeName) {
                        if (a === e) return t;
                        t++;
                    }
                }
                return 0;
            }),
            (this.getUniqueXPath = (e, n) => {
                if (n !== this.getElementByXPath(e)) {
                    const t = n.ownerDocument.evaluate(
                        e,
                        n.ownerDocument,
                        null,
                        XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
                        null
                    );
                    for (let s = 0, o = t.snapshotLength; s < o; s++) {
                        const a = "(" + e + ")[" + (s + 1) + "]";
                        if (n === this.getElementByXPath(a)) return a;
                    }
                }
                return e;
            }),
            (this.getXPathValue = (e) => {
                if (e.indexOf("'") < 0) return "'" + e + "'";
                if (e.indexOf('"') < 0) return '"' + e + '"';
                {
                    let n = "concat(",
                        t = "",
                        s = !1;
                    for (; !s; ) {
                        const o = e.indexOf("'"),
                            a = e.indexOf('"');
                        if (o < 0) {
                            (n += "'" + e + "'"), (s = !0);
                            break;
                        } else if (a < 0) {
                            (n += '"' + e + '"'), (s = !0);
                            break;
                        } else
                            a < o
                                ? ((t = e.substring(0, o)), (n += "'" + t + "'"), (e = e.substring(t.length)))
                                : ((t = e.substring(0, a)), (n += '"' + t + '"'), (e = e.substring(t.length)));
                        n += ",";
                    }
                    return (n += ")"), n;
                }
            }),
            (this.buildCssDataAttr = (e) => {
                const n = ["data-test", "data-test-id"];
                for (let t = 0; t < n.length; t++) {
                    const s = n[t],
                        o = e.getAttribute(s);
                    if (o) return "css=*[" + s + '="' + o + '"]';
                }
                return null;
            }),
            (this.buildId = (e) =>
                e.hasAttribute("id") && this.logValidation(this.validateId(e.id), "id:" + e.id) ? e.id : null),
            (this.buildLinkText = (e) => {
                if (!m.isLink(e)) return null;
                const n = e.textContent || "";
                return n.match(/^\s*$/) ? null : n.replace(/\xA0/g, " ").replace(/^\s*(.*?)\s*$/, "$1");
            }),
            (this.buildName = (e) => {
                if (e.hasAttribute("name")) {
                    const n = e.getAttribute("name");
                    if (n && this.logValidation(this.validateName(n), "name:" + n)) return n;
                }
                return null;
            }),
            (this.buildCssFinder = (e) => {
                const n = z(e);
                return n && this.logValidation(this.validateCSS(n), "css:" + n) ? n : null;
            }),
            (this.buildXPathLink = (e) => {
                if (!m.isLink(e)) return null;
                const n = e.textContent || "";
                if (n.match(/^\s*$/)) return null;
                const s = "//a[contains(text(),'" + n.replace(/^\s+/, "").replace(/\s+$/, "") + "')]",
                    o = this.getUniqueXPath(s, e);
                return o && this.logValidation(this.validateXPath(o), "xpath:" + o) ? o : null;
            }),
            (this.buildXPathImg = (e) => {
                if (!m.isImage(e)) return null;
                let n = "";
                if (e.alt) n = "//img[@alt=" + this.getXPathValue(e.alt) + "]";
                else if (e.title) n = "//img[@title=" + this.getXPathValue(e.title) + "]";
                else if (e.src) n = "//img[contains(@src," + this.getXPathValue(e.src) + ")]";
                else return null;
                const t = this.getUniqueXPath(n, e);
                return t && this.logValidation(this.validateXPath(t), "xpath:" + t) ? t : null;
            }),
            (this.buildXPathAttr = (e) => {
                const n = ["id", "name", "value", "type", "action", "onclick"],
                    t = (c, u, d) => {
                        let g = "//" + c + "[";
                        for (let f = 0; f < u.length; f++) {
                            f > 0 && (g += " and ");
                            const E = u[f],
                                q = this.getXPathValue(d[E]);
                            g += "@" + E + "=" + q;
                        }
                        return (g += "]"), this.getUniqueXPath(g, e);
                    };
                if (!e.attributes) return null;
                const s = {},
                    o = e.attributes;
                for (let c = 0; c < o.length; c++) {
                    const u = o[c];
                    s[u.name] = u.value;
                }
                const a = [];
                for (let c = 0; c < n.length; c++) {
                    const u = n[c];
                    if (!s[u]) continue;
                    a.push(u);
                    const d = t(e.nodeName.toLowerCase(), a, s);
                    if (e === this.getElementByXPath(d) && d && this.logValidation(this.validateXPath(d), "xpath:" + d))
                        return d;
                }
                return null;
            }),
            (this.buildXPathIdRelative = (e) => {
                let n = "",
                    t = e;
                for (; t; ) {
                    const s = t.parentNode;
                    if (!s) return null;
                    if (((n = this.getXPathFromParent(t) + n), m.isElement(s) && s.getAttribute("id"))) {
                        const o = s.nodeName.toLowerCase(),
                            a = this.getXPathValue(s.getAttribute("id") || ""),
                            c = "//" + o + "[@id=" + a + "]" + n,
                            u = this.getUniqueXPath(c, e);
                        if (u && this.logValidation(this.validateXPath(u), "xpath:" + u)) return u;
                    }
                    t = s;
                }
                return null;
            }),
            (this.buildXPathHref = (e) => {
                if (!e.hasAttribute("href")) return null;
                const n = e.getAttribute("href") || "";
                if (!n) return null;
                let t;
                n.search(/^http?:\/\//) >= 0
                    ? (t = "//a[@href=" + this.getXPathValue(n) + "]")
                    : (t = "//a[contains(@href, " + this.getXPathValue(n) + ")]");
                const s = this.getUniqueXPath(t, e);
                return s && this.logValidation(this.validateXPath(s), "xpath:" + s) ? s : null;
            }),
            (this.buildXPathPosition = (e) => {
                let n = "",
                    t = e;
                for (; t; ) {
                    const s = t.parentNode;
                    s ? (n = this.getXPathFromParent(t) + n) : (n = "/" + t.nodeName.toLowerCase() + n);
                    const o = "/" + n;
                    if (e === this.getElementByXPath(o) && o && this.logValidation(this.validateXPath(o), "xpath:" + o))
                        return o;
                    t = s;
                }
                return null;
            }),
            (this.buildXPathInnerText = (e) => {
                if (!(e instanceof HTMLElement) || !e.innerText) return null;
                const n = e.nodeName.toLowerCase(),
                    t = this.getXPathValue(e.innerText),
                    s = "//" + n + "[contains(.," + t + ")]",
                    o = this.getUniqueXPath(s, e);
                return o && this.logValidation(this.validateXPath(o), "xpath:" + o) ? s : null;
            }),
            (this.buildXPathInputLabel = (e) => {
                if (!m.isInput(e)) return null;
                const n = document.getElementsByTagName("LABEL"),
                    t = {};
                for (let u = 0; u < n.length; u++) {
                    const d = n[u];
                    m.isLabel(d) && d.htmlFor && document.getElementById(d.htmlFor) && (t[d.htmlFor] = d);
                }
                let s;
                if (e.id && Object.prototype.hasOwnProperty.call(e, "id")) s = t[e.id];
                else {
                    const u = e.parentNode;
                    if (!u) return null;
                    const d = [],
                        g = u.childNodes;
                    for (let f = 0; f < g.length; f++) {
                        const E = g[f];
                        m.isLabel(E) && d.push(E);
                    }
                    if (d.length !== 1) return null;
                    s = d[0];
                }
                const a = "//label[contains(.," + this.getXPathValue(s.innerText) + ")]/../input",
                    c = this.getUniqueXPath(a, e);
                return c && this.logValidation(this.validateXPath(c), "xpath:" + c) ? c : null;
            }),
            (this.window = r);
    }
}
class ue {
    constructor(r, e, n) {
        (this.setApp = (t) => {
            this.app = t;
        }),
            (this.setOnPick = (t) => {
                this.onPick = t;
            }),
            (this.setBuilder = (t) => {
                this.builder = t;
            }),
            (this.setNonStopRun = (t) => {
                this.nonStopRun = t;
            }),
            (this.addInfoBox = () => {
                const t = document.createElement("div");
                (t.id = "inspector-info-box"), (this.infoBox = t), document.body.appendChild(this.infoBox);
            }),
            (this._showPick = (t, s) => {
                const o = t.target;
                o !== s &&
                    (this._removeHighlights(),
                    o instanceof Element &&
                        (this.app === "recorder"
                            ? x(t, this.builder, { type: "verify", value: void 0 }) && this._addHighlight(o)
                            : this._addHighlight(o),
                        (s = o)));
            }),
            (this._showDivInfo = (t) => {
                t.target instanceof HTMLElement &&
                    this.infoBox &&
                    this.builder &&
                    ((this.infoBox.textContent = "No element to target"),
                    (this.infoBox.style.left = t.pageX - 8 + "px"),
                    (this.infoBox.style.top = t.pageY - 20 + "px"));
            }),
            (this._addHighlight = (t) => {
                l.debug("[picker] Adding highlight to: ", t), t.setAttribute("data-inspector-highlight", "");
            }),
            (this._removeHighlights = () => {
                l.debug("[picker] Removing highlight...");
                const t = document.querySelectorAll("[data-inspector-highlight]");
                for (let s = 0; s < t.length; s++) t[s].removeAttribute("data-inspector-highlight");
            }),
            (this._pickElement = (t) => {
                var o;
                l.debug("[picker] Picking Element:", t), t.preventDefault(), t.stopPropagation();
                const s = t.target;
                if (s instanceof HTMLElement || s instanceof SVGElement)
                    try {
                        const a = (o = this.builder) == null ? void 0 : o.build(s);
                        l.debug("[picker] Built locators:", a),
                            typeof this.onPick == "function"
                                ? (l.debug("[picker] Calling callback:", this.onPick), this.onPick(a))
                                : l.error("[picker] The onPick function is not set");
                    } catch (a) {
                        l.error(a);
                    } finally {
                        this.nonStopRun || this._removeAll();
                    }
            }),
            (this._cancelPick = (t) => {
                l.debug("[picker] Canceling Pick:", t);
                const s = t || window.event;
                (s.key === "Escape" || s.keyCode === 27) &&
                    (this._removeAll(), typeof this.onPick == "function" && this.onPick());
            }),
            (this._removeAll = () => {
                l.debug("[picker] Removing all...");
                const t = document.getElementById("inspector-frame");
                t && document.body.removeChild(t);
                const s = document.getElementById("inspector-info-box");
                s && document.body.removeChild(s),
                    document.removeEventListener("mousemove", this._showPick, !0),
                    document.removeEventListener("click", this._pickElement, !0),
                    document.removeEventListener("keydown", this._cancelPick, !0),
                    this._removeHighlights();
            }),
            (this.builder = r),
            (this.app = e || "picker"),
            (this.nonStopRun = n);
    }
}
const $ = 750,
    de = () => {
        let i = !1;
        return {
            isLocked: i,
            acquire: () =>
                b(exports, null, function* () {
                    l.debug("Acquiring lock...");
                    let n = !1;
                    for (
                        let t = 0;
                        t < 200 &&
                        (yield _(10).then(() => {
                            i === !0 && (n = !0);
                        }),
                        !n);
                        t++
                    );
                    if (!n) throw Error("Timeout while acquiring lock");
                    i = !0;
                }),
            release: () =>
                b(exports, null, function* () {
                    l.debug("Releasing lock..."), (i = !1);
                }),
        };
    };
class he {
    constructor(r, e) {
        (this.recordEvent = (t) => {
            this._removeListeners(), (this.actionsList = []);
            let s = document.getElementById("inspector-frame");
            !this.lock.isLocked &&
                !s &&
                ((s = document.createElement("div")),
                (s.id = "inspector-frame"),
                (s.className = "recorder"),
                document.body.appendChild(s)),
                (this.callback = t),
                this._addListeners();
        }),
            (this.stop = () => {
                this.callback && this.callback({ actionType: "stop", actions: void 0, url: document.URL }),
                    this.picker._removeAll(),
                    this._removeListeners();
            }),
            (this._addListeners = () => {
                document.addEventListener("mousemove", this.picker._showPick, !0),
                    document.addEventListener("click", this._handleClick, !0),
                    document.addEventListener("change", this._handleChange, !0),
                    document.addEventListener("keydown", this._handleKeyboardEvent, !0),
                    document.addEventListener("contextmenu", this._handleContextMenu, !0),
                    document.addEventListener("input", this._handleInputChange, !0);
            }),
            (this._removeListeners = () => {
                document.removeEventListener("mousemove", this.picker._showPick, !0),
                    document.removeEventListener("change", this._handleChange, !0),
                    document.removeEventListener("click", this._handleClick, !0),
                    document.removeEventListener("keydown", this._handleKeyboardEvent, !0),
                    document.removeEventListener("contextmenu", this._handleContextMenu, !0),
                    document.removeEventListener("input", this._handleInputChange, !0);
            }),
            (this._handleInputChange = (t) => {
                l.debug("[recorder] Input Change Event:", t), (this.inputEvent = t);
            }),
            (this._handleContextMenu = (t) => {
                const s = t.target;
                if (s instanceof HTMLElement || s instanceof SVGElement)
                    try {
                        t.preventDefault();
                        const o = x(t, this.builder, { type: "verify", value: void 0 });
                        if (o === void 0 || o.node === void 0) {
                            (o != null && o.skipError) || v();
                            return;
                        }
                        const a = y(p({}, o.node), { trigger: "click" });
                        l.debug("[recorder] Appending wait action:", a),
                            this.actionsList.push(a),
                            l.debug("[recorder] Event list:", this.actionsList),
                            H(s),
                            l.debug("[recorder] Passing click event through callback -> WAITING..."),
                            this._sendEvents();
                    } catch (o) {
                        l.debug("[recorder] Skipping committing wait due to error", o), v();
                    }
            }),
            (this._handleChange = (t) => {
                l.debug("[recorder] Change Event:", t);
                const s = t.target;
                if (!(s instanceof HTMLElement || s instanceof SVGElement)) return;
                const o = x(t, this.builder);
                if (o === void 0 || o.node === void 0) {
                    (o != null && o.skipError) || v();
                    return;
                }
                l.debug("[recorder] Is recording in progress:", this.lock.isLocked), this.lock.acquire();
                try {
                    if ((l.debug("[recorder] Is handled by change?:", C(o.node.type)), C(o.node.type))) {
                        const a = document.getElementById("inspector-frame") || document.createElement("div");
                        (a.className = "recorder_in_progress"),
                            l.debug("[recorder] Preventing propagation..."),
                            t.preventDefault(),
                            t.stopPropagation();
                        const c = y(p({}, o.node), { trigger: "change" });
                        l.debug("[recorder] Appending change action", c),
                            this.actionsList.push(c),
                            l.debug("[recorder] Event list:", this.actionsList),
                            l.debug("[recorder] Passing change event through callback"),
                            this._sendEvents(),
                            (() =>
                                b(this, null, function* () {
                                    return yield _($).then(() => {
                                        (a.className = "recorder"), this.lock.release();
                                    });
                                }))();
                    } else l.debug("[recorder] Skipping committing change - will be handled by onClick handler");
                } catch (a) {
                    l.debug("[recorder] Skipping committing change due to error", a), v();
                }
                (this.inputEvent = void 0), this.lock.release();
            }),
            (this._handleClick = (t) =>
                b(this, null, function* () {
                    l.info("[recorder] Click Event:", t);
                    const s = t.target;
                    if (
                        (this.inputEvent && !this.lock.isLocked && this._handleChange(this.inputEvent),
                        !(s instanceof HTMLElement || s instanceof SVGElement))
                    )
                        return;
                    if (t.detail === -1) {
                        l.debug("[recorder] Dummy click. Exiting...");
                        return;
                    }
                    const o = x(t, this.builder);
                    if (o === void 0 || o.node === void 0) {
                        (o != null && o.skipError) || v();
                        return;
                    }
                    l.debug("[recorder] Is recording in progress:", this.lock.isLocked), this.lock.acquire();
                    try {
                        if ((l.debug("[recorder] Is handled by change?:", C(o.node.type)), C(o.node.type)))
                            l.debug("[recorder] Skipping committing click - will be handled by onChange handler"),
                                this.lock.release();
                        else {
                            const a = document.getElementById("inspector-frame") || document.createElement("div");
                            (a.className = "recorder_in_progress"),
                                l.debug("[recorder] Preventing propagation..."),
                                t.preventDefault(),
                                t.stopPropagation();
                            const c = y(p({}, o.node), { trigger: "click" });
                            l.debug("[recorder] Appending click action:", c),
                                this.actionsList.push(c),
                                l.debug("[recorder] Event list:", this.actionsList),
                                l.debug("[recorder] Passing click event through callback -> RECORDING..."),
                                this._sendEvents(),
                                (() =>
                                    b(this, null, function* () {
                                        return yield _($).then(() => {
                                            l.debug("[recorder] Pushing dummy event..."),
                                                (a.className = "recorder"),
                                                s.dispatchEvent(
                                                    new MouseEvent("click", {
                                                        bubbles: !0,
                                                        cancelable: !0,
                                                        view: window,
                                                        detail: -1,
                                                    })
                                                ),
                                                this.lock.release();
                                        });
                                    }))();
                        }
                    } catch (a) {
                        l.debug("[recorder] Skipping committing click due to error", a), v();
                    }
                })),
            (this._handleKeyboardEvent = (t) => {
                const s = t || window.event;
                (s.key === "Escape" || s.keyCode === 27) && this.stop(),
                    (s.key === "Tab" || s.keyCode === 9) && this.inputEvent && this._handleChange(this.inputEvent);
            }),
            (this._sendEvents = (t) => {
                this.callback
                    ? (this.callback({ actionType: "event", actions: this.actionsList, url: document.URL }),
                      l.debug("[recorder] Successfully invoked callback:", {
                          actionType: "event",
                          action: this.actionsList,
                          url: document.URL,
                      }),
                      t && (this.actionsList = []))
                    : l.debug("[recorder] No callback function defined");
            }),
            (this.builder = r),
            (this.picker = e),
            this.picker.setApp("recorder"),
            (this.actionsList = []),
            (this.lock = de()),
            (this.inputEvent = void 0);
        const n = document.getElementById("inspector-style") || document.createElement("style");
        (n.id = "inspector-style"), (n.type = "text/css"), document.head.appendChild(n);
    }
}
const _ = (i) =>
        new Promise((r) => {
            setTimeout(r, i);
        }),
    H = (i) => {
        l.debug("Focusing on element:", i),
            i.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
        const r = document.createElement("div"),
            e = document.documentElement.getBoundingClientRect(),
            n = i.getBoundingClientRect();
        (r.id = "inspector-focus"),
            (r.style.left = `${n.left - e.left}px`),
            (r.style.top = `${n.top - e.top}px`),
            (r.style.width = `${n.width}px`),
            (r.style.height = `${n.height}px`),
            document.body.appendChild(r),
            setTimeout(() => {
                document.body.removeChild(r);
            }, 500);
    },
    v = () => {
        l.debug("Setting error state...");
        const i = document.getElementById("inspector-frame") || document.createElement("div");
        (i.className = "error"),
            setTimeout(() => {
                l.debug("Resetting error state..."), (i.className = "recorder");
            }, 1250);
    };
class ge {
    constructor() {
        (this.startPicker = (e, n) => {
            l.debug("[inspector] Starting picker..."),
                (this.onPickCallback = e),
                l.debug("[inspector] Will User Pick Non-Stop?", n),
                (this.nonStopRun = n),
                this.picker.setNonStopRun(n),
                this.picker.setOnPick(this.onPickCallback),
                this.picker._removeHighlights();
            const t = document.getElementById("inspector-frame") || document.createElement("div");
            (t.id = "inspector-frame"),
                (t.className = "picker"),
                document.body.appendChild(t),
                document.addEventListener("mousemove", this.picker._showPick, !0),
                document.addEventListener("click", this.picker._pickElement, !0),
                document.addEventListener("keydown", this.picker._cancelPick, !0);
        }),
            (this.highlightElements = (e) => {
                l.debug("[inspector] Highlighting elements:", e);
                for (let n = 0; n < e.length; n++) this.picker._addHighlight(e[n]);
            }),
            (this.describeElements = (e) => {
                l.debug("[inspector] Describing elements:", e);
                const n = [];
                for (let t = 0; t < e.length; t++) {
                    const s = e[t].cloneNode(!1).outerHTML;
                    n.push(s);
                }
                return n;
            }),
            (this.removeHighlights = () => {
                l.debug("[inspector] Removing highlights"), this.picker._removeHighlights();
            }),
            (this.cancelPick = () => {
                l.debug("[inspector] Cancelling pick and removing highlights"), this.picker._removeAll();
            }),
            (this.focusElement = (e) => H(e)),
            (this.recordEvent = (e) => (l.debug("[inspector] Recording event..."), this.recorder.recordEvent(e))),
            (this.stopRecording = () => {
                l.debug("[inspector] Stopping recording..."), (window.InspectorStop = !0), this.recorder.stop();
            }),
            (this.builder = new ce(window)),
            (this.picker = new ue(this.builder)),
            (this.recorder = new he(this.builder, this.picker)),
            (this.nonStopRun = !1),
            (this.currentPick = void 0),
            (this.onPickCallback = void 0);
        const r = document.getElementById("inspector-style") || document.createElement("style");
        (r.id = "inspector-style"), (r.type = "text/css"), document.head.appendChild(r);
    }
}
window.Inspector = new ge();
