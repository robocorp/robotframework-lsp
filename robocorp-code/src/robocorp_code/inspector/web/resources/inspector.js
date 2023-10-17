"use strict";
var Os = Object.defineProperty,
    Ms = Object.defineProperties;
var Rs = Object.getOwnPropertyDescriptors;
var pr = Object.getOwnPropertySymbols;
var Ns = Object.prototype.hasOwnProperty,
    Gs = Object.prototype.propertyIsEnumerable;
var Er = (e, A, t) => (A in e ? Os(e, A, { enumerable: !0, configurable: !0, writable: !0, value: t }) : (e[A] = t)),
    DA = (e, A) => {
        for (var t in A || (A = {})) Ns.call(A, t) && Er(e, t, A[t]);
        if (pr) for (var t of pr(A)) Gs.call(A, t) && Er(e, t, A[t]);
        return e;
    },
    Ae = (e, A) => Ms(e, Rs(A));
var UA = (e, A, t) =>
    new Promise((r, n) => {
        var s = (a) => {
                try {
                    i(t.next(a));
                } catch (o) {
                    n(o);
                }
            },
            B = (a) => {
                try {
                    i(t.throw(a));
                } catch (o) {
                    n(o);
                }
            },
            i = (a) => (a.done ? r(a.value) : Promise.resolve(a.value).then(s, B));
        i((t = t.apply(e, A)).next());
    });
let aA, Qr;
function Vs(e, A) {
    if (e.nodeType !== Node.ELEMENT_NODE) throw new Error("Can't generate CSS selector for non-element node type.");
    if (e.tagName.toLowerCase() === "html") return "html";
    const t = {
        root: document.body,
        idName: (n) => !0,
        className: (n) => !0,
        tagName: (n) => !0,
        attr: (n, s) => !1,
        seedMinLength: 1,
        optimizedMinLength: 2,
        threshold: 1e3,
        maxNumberOfTries: 1e4,
    };
    (aA = DA(DA({}, t), A)), (Qr = ks(aA.root, t));
    let r = pe(e, "all", () => pe(e, "two", () => pe(e, "one", () => pe(e, "none"))));
    if (r) {
        const n = Kn(bn(r, e));
        return n.length > 0 && (r = n[0]), ct(r);
    } else throw new Error("Selector was not found.");
}
function ks(e, A) {
    return e.nodeType === Node.DOCUMENT_NODE ? e : e === A.root ? e.ownerDocument : e;
}
function pe(e, A, t) {
    let r = null,
        n = [],
        s = e,
        B = 0;
    for (; s; ) {
        let i = He(Ps(s)) || He(..._s(s)) || He(...Xs(s)) || He(Js(s)) || [Ir()];
        const a = Ys(s);
        if (A == "all") a && (i = i.concat(i.filter(dt).map((o) => Ee(o, a))));
        else if (A == "two") (i = i.slice(0, 1)), a && (i = i.concat(i.filter(dt).map((o) => Ee(o, a))));
        else if (A == "one") {
            const [o] = (i = i.slice(0, 1));
            a && dt(o) && (i = [Ee(o, a)]);
        } else A == "none" && ((i = [Ir()]), a && (i = [Ee(i[0], a)]));
        for (let o of i) o.level = B;
        if ((n.push(i), n.length >= aA.seedMinLength && ((r = Hr(n, t)), r))) break;
        (s = s.parentElement), B++;
    }
    return r || (r = Hr(n, t)), !r && t ? t() : r;
}
function Hr(e, A) {
    const t = Kn(Ln(e));
    if (t.length > aA.threshold) return A ? A() : null;
    for (let r of t) if (yn(r)) return r;
    return null;
}
function ct(e) {
    let A = e[0],
        t = A.name;
    for (let r = 1; r < e.length; r++) {
        const n = e[r].level || 0;
        A.level === n - 1 ? (t = `${e[r].name} > ${t}`) : (t = `${e[r].name} ${t}`), (A = e[r]);
    }
    return t;
}
function vr(e) {
    return e.map((A) => A.penalty).reduce((A, t) => A + t, 0);
}
function yn(e) {
    const A = ct(e);
    switch (Qr.querySelectorAll(A).length) {
        case 0:
            throw new Error(`Can't select any node with this selector: ${A}`);
        case 1:
            return !0;
        default:
            return !1;
    }
}
function Ps(e) {
    const A = e.getAttribute("id");
    return A && aA.idName(A) ? { name: "#" + CSS.escape(A), penalty: 0 } : null;
}
function _s(e) {
    return Array.from(e.attributes)
        .filter((t) => aA.attr(t.name, t.value))
        .map((t) => ({ name: `[${CSS.escape(t.name)}="${CSS.escape(t.value)}"]`, penalty: 0.5 }));
}
function Xs(e) {
    return Array.from(e.classList)
        .filter(aA.className)
        .map((t) => ({ name: "." + CSS.escape(t), penalty: 1 }));
}
function Js(e) {
    const A = e.tagName.toLowerCase();
    return aA.tagName(A) ? { name: A, penalty: 2 } : null;
}
function Ir() {
    return { name: "*", penalty: 3 };
}
function Ys(e) {
    const A = e.parentNode;
    if (!A) return null;
    let t = A.firstChild;
    if (!t) return null;
    let r = 0;
    for (; t && (t.nodeType === Node.ELEMENT_NODE && r++, t !== e); ) t = t.nextSibling;
    return r;
}
function Ee(e, A) {
    return { name: e.name + `:nth-child(${A})`, penalty: e.penalty + 1 };
}
function dt(e) {
    return e.name !== "html" && !e.name.startsWith("#");
}
function He(...e) {
    const A = e.filter(Ws);
    return A.length > 0 ? A : null;
}
function Ws(e) {
    return e != null;
}
function* Ln(e, A = []) {
    if (e.length > 0) for (let t of e[0]) yield* Ln(e.slice(1, e.length), A.concat(t));
    else yield A;
}
function Kn(e) {
    return [...e].sort((A, t) => vr(A) - vr(t));
}
function* bn(e, A, t = { counter: 0, visited: new Map() }) {
    if (e.length > 2 && e.length > aA.optimizedMinLength)
        for (let r = 1; r < e.length - 1; r++) {
            if (t.counter > aA.maxNumberOfTries) return;
            t.counter += 1;
            const n = [...e];
            n.splice(r, 1);
            const s = ct(n);
            if (t.visited.has(s)) return;
            yn(n) && Zs(n, A) && (yield n, t.visited.set(s, !0), yield* bn(n, A, t));
        }
}
function Zs(e, A) {
    return Qr.querySelector(ct(e)) === A;
}
/*!
 * html2canvas 1.4.1 <https://html2canvas.hertzen.com>
 * Copyright (c) 2022 Niklas von Hertzen <https://hertzen.com>
 * Released under MIT License
 */ /*! *****************************************************************************
Copyright (c) Microsoft Corporation.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.
***************************************************************************** */ var Pt = function (e, A) {
    return (
        (Pt =
            Object.setPrototypeOf ||
            ({ __proto__: [] } instanceof Array &&
                function (t, r) {
                    t.__proto__ = r;
                }) ||
            function (t, r) {
                for (var n in r) Object.prototype.hasOwnProperty.call(r, n) && (t[n] = r[n]);
            }),
        Pt(e, A)
    );
};
function sA(e, A) {
    if (typeof A != "function" && A !== null)
        throw new TypeError("Class extends value " + String(A) + " is not a constructor or null");
    Pt(e, A);
    function t() {
        this.constructor = e;
    }
    e.prototype = A === null ? Object.create(A) : ((t.prototype = A.prototype), new t());
}
var _t = function () {
    return (
        (_t =
            Object.assign ||
            function (A) {
                for (var t, r = 1, n = arguments.length; r < n; r++) {
                    t = arguments[r];
                    for (var s in t) Object.prototype.hasOwnProperty.call(t, s) && (A[s] = t[s]);
                }
                return A;
            }),
        _t.apply(this, arguments)
    );
};
function J(e, A, t, r) {
    function n(s) {
        return s instanceof t
            ? s
            : new t(function (B) {
                  B(s);
              });
    }
    return new (t || (t = Promise))(function (s, B) {
        function i(c) {
            try {
                o(r.next(c));
            } catch (l) {
                B(l);
            }
        }
        function a(c) {
            try {
                o(r.throw(c));
            } catch (l) {
                B(l);
            }
        }
        function o(c) {
            c.done ? s(c.value) : n(c.value).then(i, a);
        }
        o((r = r.apply(e, A || [])).next());
    });
}
function _(e, A) {
    var t = {
            label: 0,
            sent: function () {
                if (s[0] & 1) throw s[1];
                return s[1];
            },
            trys: [],
            ops: [],
        },
        r,
        n,
        s,
        B;
    return (
        (B = { next: i(0), throw: i(1), return: i(2) }),
        typeof Symbol == "function" &&
            (B[Symbol.iterator] = function () {
                return this;
            }),
        B
    );
    function i(o) {
        return function (c) {
            return a([o, c]);
        };
    }
    function a(o) {
        if (r) throw new TypeError("Generator is already executing.");
        for (; t; )
            try {
                if (
                    ((r = 1),
                    n &&
                        (s = o[0] & 2 ? n.return : o[0] ? n.throw || ((s = n.return) && s.call(n), 0) : n.next) &&
                        !(s = s.call(n, o[1])).done)
                )
                    return s;
                switch (((n = 0), s && (o = [o[0] & 2, s.value]), o[0])) {
                    case 0:
                    case 1:
                        s = o;
                        break;
                    case 4:
                        return t.label++, { value: o[1], done: !1 };
                    case 5:
                        t.label++, (n = o[1]), (o = [0]);
                        continue;
                    case 7:
                        (o = t.ops.pop()), t.trys.pop();
                        continue;
                    default:
                        if (((s = t.trys), !(s = s.length > 0 && s[s.length - 1]) && (o[0] === 6 || o[0] === 2))) {
                            t = 0;
                            continue;
                        }
                        if (o[0] === 3 && (!s || (o[1] > s[0] && o[1] < s[3]))) {
                            t.label = o[1];
                            break;
                        }
                        if (o[0] === 6 && t.label < s[1]) {
                            (t.label = s[1]), (s = o);
                            break;
                        }
                        if (s && t.label < s[2]) {
                            (t.label = s[2]), t.ops.push(o);
                            break;
                        }
                        s[2] && t.ops.pop(), t.trys.pop();
                        continue;
                }
                o = A.call(e, t);
            } catch (c) {
                (o = [6, c]), (n = 0);
            } finally {
                r = s = 0;
            }
        if (o[0] & 5) throw o[1];
        return { value: o[0] ? o[1] : void 0, done: !0 };
    }
}
function ve(e, A, t) {
    if (t || arguments.length === 2)
        for (var r = 0, n = A.length, s; r < n; r++)
            (s || !(r in A)) && (s || (s = Array.prototype.slice.call(A, 0, r)), (s[r] = A[r]));
    return e.concat(s || A);
}
var fA = (function () {
        function e(A, t, r, n) {
            (this.left = A), (this.top = t), (this.width = r), (this.height = n);
        }
        return (
            (e.prototype.add = function (A, t, r, n) {
                return new e(this.left + A, this.top + t, this.width + r, this.height + n);
            }),
            (e.fromClientRect = function (A, t) {
                return new e(t.left + A.windowBounds.left, t.top + A.windowBounds.top, t.width, t.height);
            }),
            (e.fromDOMRectList = function (A, t) {
                var r = Array.from(t).find(function (n) {
                    return n.width !== 0;
                });
                return r ? new e(r.left + A.windowBounds.left, r.top + A.windowBounds.top, r.width, r.height) : e.EMPTY;
            }),
            (e.EMPTY = new e(0, 0, 0, 0)),
            e
        );
    })(),
    lt = function (e, A) {
        return fA.fromClientRect(e, A.getBoundingClientRect());
    },
    qs = function (e) {
        var A = e.body,
            t = e.documentElement;
        if (!A || !t) throw new Error("Unable to get document size");
        var r = Math.max(
                Math.max(A.scrollWidth, t.scrollWidth),
                Math.max(A.offsetWidth, t.offsetWidth),
                Math.max(A.clientWidth, t.clientWidth)
            ),
            n = Math.max(
                Math.max(A.scrollHeight, t.scrollHeight),
                Math.max(A.offsetHeight, t.offsetHeight),
                Math.max(A.clientHeight, t.clientHeight)
            );
        return new fA(0, 0, r, n);
    },
    gt = function (e) {
        for (var A = [], t = 0, r = e.length; t < r; ) {
            var n = e.charCodeAt(t++);
            if (n >= 55296 && n <= 56319 && t < r) {
                var s = e.charCodeAt(t++);
                (s & 64512) === 56320 ? A.push(((n & 1023) << 10) + (s & 1023) + 65536) : (A.push(n), t--);
            } else A.push(n);
        }
        return A;
    },
    O = function () {
        for (var e = [], A = 0; A < arguments.length; A++) e[A] = arguments[A];
        if (String.fromCodePoint) return String.fromCodePoint.apply(String, e);
        var t = e.length;
        if (!t) return "";
        for (var r = [], n = -1, s = ""; ++n < t; ) {
            var B = e[n];
            B <= 65535 ? r.push(B) : ((B -= 65536), r.push((B >> 10) + 55296, (B % 1024) + 56320)),
                (n + 1 === t || r.length > 16384) && ((s += String.fromCharCode.apply(String, r)), (r.length = 0));
        }
        return s;
    },
    mr = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
    js = typeof Uint8Array == "undefined" ? [] : new Uint8Array(256);
for (var Ie = 0; Ie < mr.length; Ie++) js[mr.charCodeAt(Ie)] = Ie;
var yr = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
    se = typeof Uint8Array == "undefined" ? [] : new Uint8Array(256);
for (var me = 0; me < yr.length; me++) se[yr.charCodeAt(me)] = me;
var zs = function (e) {
        var A = e.length * 0.75,
            t = e.length,
            r,
            n = 0,
            s,
            B,
            i,
            a;
        e[e.length - 1] === "=" && (A--, e[e.length - 2] === "=" && A--);
        var o =
                typeof ArrayBuffer != "undefined" &&
                typeof Uint8Array != "undefined" &&
                typeof Uint8Array.prototype.slice != "undefined"
                    ? new ArrayBuffer(A)
                    : new Array(A),
            c = Array.isArray(o) ? o : new Uint8Array(o);
        for (r = 0; r < t; r += 4)
            (s = se[e.charCodeAt(r)]),
                (B = se[e.charCodeAt(r + 1)]),
                (i = se[e.charCodeAt(r + 2)]),
                (a = se[e.charCodeAt(r + 3)]),
                (c[n++] = (s << 2) | (B >> 4)),
                (c[n++] = ((B & 15) << 4) | (i >> 2)),
                (c[n++] = ((i & 3) << 6) | (a & 63));
        return o;
    },
    $s = function (e) {
        for (var A = e.length, t = [], r = 0; r < A; r += 2) t.push((e[r + 1] << 8) | e[r]);
        return t;
    },
    AB = function (e) {
        for (var A = e.length, t = [], r = 0; r < A; r += 4)
            t.push((e[r + 3] << 24) | (e[r + 2] << 16) | (e[r + 1] << 8) | e[r]);
        return t;
    },
    RA = 5,
    wr = 6 + 5,
    pt = 2,
    eB = wr - RA,
    xn = 65536 >> RA,
    tB = 1 << RA,
    Et = tB - 1,
    rB = 1024 >> RA,
    nB = xn + rB,
    sB = nB,
    BB = 32,
    iB = sB + BB,
    aB = 65536 >> wr,
    oB = 1 << eB,
    cB = oB - 1,
    Lr = function (e, A, t) {
        return e.slice ? e.slice(A, t) : new Uint16Array(Array.prototype.slice.call(e, A, t));
    },
    lB = function (e, A, t) {
        return e.slice ? e.slice(A, t) : new Uint32Array(Array.prototype.slice.call(e, A, t));
    },
    gB = function (e, A) {
        var t = zs(e),
            r = Array.isArray(t) ? AB(t) : new Uint32Array(t),
            n = Array.isArray(t) ? $s(t) : new Uint16Array(t),
            s = 24,
            B = Lr(n, s / 2, r[4] / 2),
            i = r[5] === 2 ? Lr(n, (s + r[4]) / 2) : lB(r, Math.ceil((s + r[4]) / 4));
        return new uB(r[0], r[1], r[2], r[3], B, i);
    },
    uB = (function () {
        function e(A, t, r, n, s, B) {
            (this.initialValue = A),
                (this.errorValue = t),
                (this.highStart = r),
                (this.highValueIndex = n),
                (this.index = s),
                (this.data = B);
        }
        return (
            (e.prototype.get = function (A) {
                var t;
                if (A >= 0) {
                    if (A < 55296 || (A > 56319 && A <= 65535))
                        return (t = this.index[A >> RA]), (t = (t << pt) + (A & Et)), this.data[t];
                    if (A <= 65535)
                        return (t = this.index[xn + ((A - 55296) >> RA)]), (t = (t << pt) + (A & Et)), this.data[t];
                    if (A < this.highStart)
                        return (
                            (t = iB - aB + (A >> wr)),
                            (t = this.index[t]),
                            (t += (A >> RA) & cB),
                            (t = this.index[t]),
                            (t = (t << pt) + (A & Et)),
                            this.data[t]
                        );
                    if (A <= 1114111) return this.data[this.highValueIndex];
                }
                return this.errorValue;
            }),
            e
        );
    })(),
    Kr = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
    QB = typeof Uint8Array == "undefined" ? [] : new Uint8Array(256);
for (var ye = 0; ye < Kr.length; ye++) QB[Kr.charCodeAt(ye)] = ye;
var wB =
        "KwAAAAAAAAAACA4AUD0AADAgAAACAAAAAAAIABAAGABAAEgAUABYAGAAaABgAGgAYgBqAF8AZwBgAGgAcQB5AHUAfQCFAI0AlQCdAKIAqgCyALoAYABoAGAAaABgAGgAwgDKAGAAaADGAM4A0wDbAOEA6QDxAPkAAQEJAQ8BFwF1AH0AHAEkASwBNAE6AUIBQQFJAVEBWQFhAWgBcAF4ATAAgAGGAY4BlQGXAZ8BpwGvAbUBvQHFAc0B0wHbAeMB6wHxAfkBAQIJAvEBEQIZAiECKQIxAjgCQAJGAk4CVgJeAmQCbAJ0AnwCgQKJApECmQKgAqgCsAK4ArwCxAIwAMwC0wLbAjAA4wLrAvMC+AIAAwcDDwMwABcDHQMlAy0DNQN1AD0DQQNJA0kDSQNRA1EDVwNZA1kDdQB1AGEDdQBpA20DdQN1AHsDdQCBA4kDkQN1AHUAmQOhA3UAdQB1AHUAdQB1AHUAdQB1AHUAdQB1AHUAdQB1AHUAdQB1AKYDrgN1AHUAtgO+A8YDzgPWAxcD3gPjA+sD8wN1AHUA+wMDBAkEdQANBBUEHQQlBCoEFwMyBDgEYABABBcDSARQBFgEYARoBDAAcAQzAXgEgASIBJAEdQCXBHUAnwSnBK4EtgS6BMIEyAR1AHUAdQB1AHUAdQCVANAEYABgAGAAYABgAGAAYABgANgEYADcBOQEYADsBPQE/AQEBQwFFAUcBSQFLAU0BWQEPAVEBUsFUwVbBWAAYgVgAGoFcgV6BYIFigWRBWAAmQWfBaYFYABgAGAAYABgAKoFYACxBbAFuQW6BcEFwQXHBcEFwQXPBdMF2wXjBeoF8gX6BQIGCgYSBhoGIgYqBjIGOgZgAD4GRgZMBmAAUwZaBmAAYABgAGAAYABgAGAAYABgAGAAYABgAGIGYABpBnAGYABgAGAAYABgAGAAYABgAGAAYAB4Bn8GhQZgAGAAYAB1AHcDFQSLBmAAYABgAJMGdQA9A3UAmwajBqsGqwaVALMGuwbDBjAAywbSBtIG1QbSBtIG0gbSBtIG0gbdBuMG6wbzBvsGAwcLBxMHAwcbByMHJwcsBywHMQcsB9IGOAdAB0gHTgfSBkgHVgfSBtIG0gbSBtIG0gbSBtIG0gbSBiwHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAdgAGAALAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAdbB2MHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsB2kH0gZwB64EdQB1AHUAdQB1AHUAdQB1AHUHfQdgAIUHjQd1AHUAlQedB2AAYAClB6sHYACzB7YHvgfGB3UAzgfWBzMB3gfmB1EB7gf1B/0HlQENAQUIDQh1ABUIHQglCBcDLQg1CD0IRQhNCEEDUwh1AHUAdQBbCGMIZAhlCGYIZwhoCGkIYwhkCGUIZghnCGgIaQhjCGQIZQhmCGcIaAhpCGMIZAhlCGYIZwhoCGkIYwhkCGUIZghnCGgIaQhjCGQIZQhmCGcIaAhpCGMIZAhlCGYIZwhoCGkIYwhkCGUIZghnCGgIaQhjCGQIZQhmCGcIaAhpCGMIZAhlCGYIZwhoCGkIYwhkCGUIZghnCGgIaQhjCGQIZQhmCGcIaAhpCGMIZAhlCGYIZwhoCGkIYwhkCGUIZghnCGgIaQhjCGQIZQhmCGcIaAhpCGMIZAhlCGYIZwhoCGkIYwhkCGUIZghnCGgIaQhjCGQIZQhmCGcIaAhpCGMIZAhlCGYIZwhoCGkIYwhkCGUIZghnCGgIaQhjCGQIZQhmCGcIaAhpCGMIZAhlCGYIZwhoCGkIYwhkCGUIZghnCGgIaQhjCGQIZQhmCGcIaAhpCGMIZAhlCGYIZwhoCGkIYwhkCGUIZghnCGgIaQhjCGQIZQhmCGcIaAhpCGMIZAhlCGYIZwhoCGkIYwhkCGUIZghnCGgIaQhjCGQIZQhmCGcIaAhpCGMIZAhlCGYIZwhoCGkIYwhkCGUIZghnCGgIaQhjCGQIZQhmCGcIaAhpCGMIZAhlCGYIZwhoCGkIYwhkCGUIZghnCGgIaQhjCGQIZQhmCGcIaAhpCGMIZAhlCGYIZwhoCGkIYwhkCGUIZghnCGgIaQhjCGQIZQhmCGcIaAhpCGMIZAhlCGYIZwhoCGkIYwhkCGUIZghnCGgIaQhjCGQIZQhmCGcIaAhpCGMIZAhlCGYIZwhoCGkIYwhkCGUIZghnCGgIaQhjCGQIZQhmCGcIaAhpCGMIZAhlCGYIZwhoCGkIYwhkCGUIZghnCGgIaQhjCGQIZQhmCGcIaAhpCGMIZAhlCGYIZwhoCGkIYwhkCGUIZghnCGgIcAh3CHoIMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwAIIIggiCCIIIggiCCIIIggiCCIIIggiCCIIIggiCCIIIggiCCIIIggiCCIIIggiCCIIIggiCCIIIggiCCIIIgggwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAALAcsBywHLAcsBywHLAcsBywHLAcsB4oILAcsB44I0gaWCJ4Ipgh1AHUAqgiyCHUAdQB1AHUAdQB1AHUAdQB1AHUAtwh8AXUAvwh1AMUIyQjRCNkI4AjoCHUAdQB1AO4I9gj+CAYJDgkTCS0HGwkjCYIIggiCCIIIggiCCIIIggiCCIIIggiCCIIIggiCCIIIggiCCIIIggiCCIIIggiCCIIIggiCCIIIggiCCIIIggiAAIAAAAFAAYABgAGIAXwBgAHEAdQBFAJUAogCyAKAAYABgAEIA4ABGANMA4QDxAMEBDwE1AFwBLAE6AQEBUQF4QkhCmEKoQrhCgAHIQsAB0MLAAcABwAHAAeDC6ABoAHDCwMMAAcABwAHAAdDDGMMAAcAB6MM4wwjDWMNow3jDaABoAGgAaABoAGgAaABoAGgAaABoAGgAaABoAGgAaABoAGgAaABoAEjDqABWw6bDqABpg6gAaABoAHcDvwOPA+gAaABfA/8DvwO/A78DvwO/A78DvwO/A78DvwO/A78DvwO/A78DvwO/A78DvwO/A78DvwO/A78DvwO/A78DpcPAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcAB9cPKwkyCToJMAB1AHUAdQBCCUoJTQl1AFUJXAljCWcJawkwADAAMAAwAHMJdQB2CX4JdQCECYoJjgmWCXUAngkwAGAAYABxAHUApgn3A64JtAl1ALkJdQDACTAAMAAwADAAdQB1AHUAdQB1AHUAdQB1AHUAowYNBMUIMAAwADAAMADICcsJ0wnZCRUE4QkwAOkJ8An4CTAAMAB1AAAKvwh1AAgKDwoXCh8KdQAwACcKLgp1ADYKqAmICT4KRgowADAAdQB1AE4KMAB1AFYKdQBeCnUAZQowADAAMAAwADAAMAAwADAAMAAVBHUAbQowADAAdQC5CXUKMAAwAHwBxAijBogEMgF9CoQKiASMCpQKmgqIBKIKqgquCogEDQG2Cr4KxgrLCjAAMADTCtsKCgHjCusK8Qr5CgELMAAwADAAMAB1AIsECQsRC3UANAEZCzAAMAAwADAAMAB1ACELKQswAHUANAExCzkLdQBBC0kLMABRC1kLMAAwADAAMAAwADAAdQBhCzAAMAAwAGAAYABpC3ELdwt/CzAAMACHC4sLkwubC58Lpwt1AK4Ltgt1APsDMAAwADAAMAAwADAAMAAwAL4LwwvLC9IL1wvdCzAAMADlC+kL8Qv5C/8LSQswADAAMAAwADAAMAAwADAAMAAHDDAAMAAwADAAMAAODBYMHgx1AHUAdQB1AHUAdQB1AHUAdQB1AHUAdQB1AHUAdQB1AHUAdQB1AHUAdQB1AHUAdQB1AHUAdQB1ACYMMAAwADAAdQB1AHUALgx1AHUAdQB1AHUAdQA2DDAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwAHUAdQB1AHUAdQB1AHUAdQB1AHUAdQB1AHUAdQB1AHUAdQB1AD4MdQBGDHUAdQB1AHUAdQB1AEkMdQB1AHUAdQB1AFAMMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwAHUAdQB1AHUAdQB1AHUAdQB1AHUAdQB1AHUAdQBYDHUAdQB1AF8MMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAB1AHUAdQB1AHUAdQB1AHUAdQB1AHUAdQB1AHUAdQB1AHUA+wMVBGcMMAAwAHwBbwx1AHcMfwyHDI8MMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAYABgAJcMMAAwADAAdQB1AJ8MlQClDDAAMACtDCwHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsB7UMLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHdQB1AHUAdQB1AHUAdQB1AHUAdQB1AHUAdQB1AA0EMAC9DDAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAsBywHLAcsBywHLAcsBywHLQcwAMEMyAwsBywHLAcsBywHLAcsBywHLAcsBywHzAwwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwAHUAdQB1ANQM2QzhDDAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMABgAGAAYABgAGAAYABgAOkMYADxDGAA+AwADQYNYABhCWAAYAAODTAAMAAwADAAFg1gAGAAHg37AzAAMAAwADAAYABgACYNYAAsDTQNPA1gAEMNPg1LDWAAYABgAGAAYABgAGAAYABgAGAAUg1aDYsGVglhDV0NcQBnDW0NdQ15DWAAYABgAGAAYABgAGAAYABgAGAAYABgAGAAYABgAGAAlQCBDZUAiA2PDZcNMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAnw2nDTAAMAAwADAAMAAwAHUArw23DTAAMAAwADAAMAAwADAAMAAwADAAMAB1AL8NMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAB1AHUAdQB1AHUAdQDHDTAAYABgAM8NMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAA1w11ANwNMAAwAD0B5A0wADAAMAAwADAAMADsDfQN/A0EDgwOFA4wABsOMAAwADAAMAAwADAAMAAwANIG0gbSBtIG0gbSBtIG0gYjDigOwQUuDsEFMw7SBjoO0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIGQg5KDlIOVg7SBtIGXg5lDm0OdQ7SBtIGfQ6EDooOjQ6UDtIGmg6hDtIG0gaoDqwO0ga0DrwO0gZgAGAAYADEDmAAYAAkBtIGzA5gANIOYADaDokO0gbSBt8O5w7SBu8O0gb1DvwO0gZgAGAAxA7SBtIG0gbSBtIGYABgAGAAYAAED2AAsAUMD9IG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIGFA8sBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAccD9IGLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHJA8sBywHLAcsBywHLAccDywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywPLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAc0D9IG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIGLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAccD9IG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIGFA8sBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHLAcsBywHPA/SBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gbSBtIG0gYUD0QPlQCVAJUAMAAwADAAMACVAJUAlQCVAJUAlQCVAEwPMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAA//8EAAQABAAEAAQABAAEAAQABAANAAMAAQABAAIABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQACgATABcAHgAbABoAHgAXABYAEgAeABsAGAAPABgAHABLAEsASwBLAEsASwBLAEsASwBLABgAGAAeAB4AHgATAB4AUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQABYAGwASAB4AHgAeAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAWAA0AEQAeAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArAAQABAAEAAQABAAFAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAJABYAGgAbABsAGwAeAB0AHQAeAE8AFwAeAA0AHgAeABoAGwBPAE8ADgBQAB0AHQAdAE8ATwAXAE8ATwBPABYAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAB0AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAdAFAAUABQAFAAUABQAFAAUAAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAFAAHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAeAB4AHgAeAFAATwBAAE8ATwBPAEAATwBQAFAATwBQAB4AHgAeAB4AHgAeAB0AHQAdAB0AHgAdAB4ADgBQAFAAUABQAFAAHgAeAB4AHgAeAB4AHgBQAB4AUAAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4ABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAJAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAkACQAJAAkACQAJAAkABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAeAB4AHgAeAFAAHgAeAB4AKwArAFAAUABQAFAAGABQACsAKwArACsAHgAeAFAAHgBQAFAAUAArAFAAKwAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AKwAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4ABAAEAAQABAAEAAQABAAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsAUAAeAB4AHgAeAB4AHgBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAYAA0AKwArAB4AHgAbACsABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQADQAEAB4ABAAEAB4ABAAEABMABAArACsAKwArACsAKwArACsAVgBWAFYAVgBWAFYAVgBWAFYAVgBWAFYAVgBWAFYAVgBWAFYAVgBWAFYAVgBWAFYAVgBWAFYAKwArACsAKwBWAFYAVgBWAB4AHgArACsAKwArACsAKwArACsAKwArACsAHgAeAB4AHgAeAB4AHgAeAB4AGgAaABoAGAAYAB4AHgAEAAQABAAEAAQABAAEAAQABAAEAAQAEwAEACsAEwATAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABABLAEsASwBLAEsASwBLAEsASwBLABoAGQAZAB4AUABQAAQAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQABMAUAAEAAQABAAEAAQABAAEAB4AHgAEAAQABAAEAAQABABQAFAABAAEAB4ABAAEAAQABABQAFAASwBLAEsASwBLAEsASwBLAEsASwBQAFAAUAAeAB4AUAAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AKwAeAFAABABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAABAAEAAQABAAEAAQABAAEAAQABAAEAFAAKwArACsAKwArACsAKwArACsAKwArACsAKwArAEsASwBLAEsASwBLAEsASwBLAEsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAABAAEAAQABAAEAAQABAAEAAQAUABQAB4AHgAYABMAUAArACsABAAbABsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAEAAQABAAEAFAABAAEAAQABAAEAFAABAAEAAQAUAAEAAQABAAEAAQAKwArAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAEAAQABAArACsAHgArAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArAFAAUABQAFAAUABQAFAAUABQAFAAKwArACsAKwArACsAKwArACsAKwArAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAB4ABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAAQABAAEAFAABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQAUAAEAAQABAAEAAQABAAEAFAAUABQAFAAUABQAFAAUABQAFAABAAEAA0ADQBLAEsASwBLAEsASwBLAEsASwBLAB4AUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAEAAQABAArAFAAUABQAFAAUABQAFAAUAArACsAUABQACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwBQAFAAUABQAFAAUABQACsAUAArACsAKwBQAFAAUABQACsAKwAEAFAABAAEAAQABAAEAAQABAArACsABAAEACsAKwAEAAQABABQACsAKwArACsAKwArACsAKwAEACsAKwArACsAUABQACsAUABQAFAABAAEACsAKwBLAEsASwBLAEsASwBLAEsASwBLAFAAUAAaABoAUABQAFAAUABQAEwAHgAbAFAAHgAEACsAKwAEAAQABAArAFAAUABQAFAAUABQACsAKwArACsAUABQACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwBQAFAAUABQAFAAUABQACsAUABQACsAUABQACsAUABQACsAKwAEACsABAAEAAQABAAEACsAKwArACsABAAEACsAKwAEAAQABAArACsAKwAEACsAKwArACsAKwArACsAUABQAFAAUAArAFAAKwArACsAKwArACsAKwBLAEsASwBLAEsASwBLAEsASwBLAAQABABQAFAAUAAEAB4AKwArACsAKwArACsAKwArACsAKwAEAAQABAArAFAAUABQAFAAUABQAFAAUABQACsAUABQAFAAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwBQAFAAUABQAFAAUABQACsAUABQACsAUABQAFAAUABQACsAKwAEAFAABAAEAAQABAAEAAQABAAEACsABAAEAAQAKwAEAAQABAArACsAUAArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwBQAFAABAAEACsAKwBLAEsASwBLAEsASwBLAEsASwBLAB4AGwArACsAKwArACsAKwArAFAABAAEAAQABAAEAAQAKwAEAAQABAArAFAAUABQAFAAUABQAFAAUAArACsAUABQACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAAQABAAEAAQABAArACsABAAEACsAKwAEAAQABAArACsAKwArACsAKwArAAQABAAEACsAKwArACsAUABQACsAUABQAFAABAAEACsAKwBLAEsASwBLAEsASwBLAEsASwBLAB4AUABQAFAAUABQAFAAUAArACsAKwArACsAKwArACsAKwArAAQAUAArAFAAUABQAFAAUABQACsAKwArAFAAUABQACsAUABQAFAAUAArACsAKwBQAFAAKwBQACsAUABQACsAKwArAFAAUAArACsAKwBQAFAAUAArACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsAKwArAAQABAAEAAQABAArACsAKwAEAAQABAArAAQABAAEAAQAKwArAFAAKwArACsAKwArACsABAArACsAKwArACsAKwArACsAKwArAEsASwBLAEsASwBLAEsASwBLAEsAUABQAFAAHgAeAB4AHgAeAB4AGwAeACsAKwArACsAKwAEAAQABAAEAAQAUABQAFAAUABQAFAAUABQACsAUABQAFAAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwArACsAUAAEAAQABAAEAAQABAAEACsABAAEAAQAKwAEAAQABAAEACsAKwArACsAKwArACsABAAEACsAUABQAFAAKwArACsAKwArAFAAUAAEAAQAKwArAEsASwBLAEsASwBLAEsASwBLAEsAKwArACsAKwArACsAKwAOAFAAUABQAFAAUABQAFAAHgBQAAQABAAEAA4AUABQAFAAUABQAFAAUABQACsAUABQAFAAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArAFAAUABQAFAAUABQAFAAUABQAFAAKwBQAFAAUABQAFAAKwArAAQAUAAEAAQABAAEAAQABAAEACsABAAEAAQAKwAEAAQABAAEACsAKwArACsAKwArACsABAAEACsAKwArACsAKwArACsAUAArAFAAUAAEAAQAKwArAEsASwBLAEsASwBLAEsASwBLAEsAKwBQAFAAKwArACsAKwArACsAKwArACsAKwArACsAKwAEAAQABAAEAFAAUABQAFAAUABQAFAAUABQACsAUABQAFAAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAABAAEAFAABAAEAAQABAAEAAQABAArAAQABAAEACsABAAEAAQABABQAB4AKwArACsAKwBQAFAAUAAEAFAAUABQAFAAUABQAFAAUABQAFAABAAEACsAKwBLAEsASwBLAEsASwBLAEsASwBLAFAAUABQAFAAUABQAFAAUABQABoAUABQAFAAUABQAFAAKwAEAAQABAArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArAFAAUABQAFAAUABQAFAAUABQACsAUAArACsAUABQAFAAUABQAFAAUAArACsAKwAEACsAKwArACsABAAEAAQABAAEAAQAKwAEACsABAAEAAQABAAEAAQABAAEACsAKwArACsAKwArAEsASwBLAEsASwBLAEsASwBLAEsAKwArAAQABAAeACsAKwArACsAKwArACsAKwArACsAKwArAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXAAqAFwAXAAqACoAKgAqACoAKgAqACsAKwArACsAGwBcAFwAXABcAFwAXABcACoAKgAqACoAKgAqACoAKgAeAEsASwBLAEsASwBLAEsASwBLAEsADQANACsAKwArACsAKwBcAFwAKwBcACsAXABcAFwAXABcACsAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcACsAXAArAFwAXABcAFwAXABcAFwAXABcAFwAKgBcAFwAKgAqACoAKgAqACoAKgAqACoAXAArACsAXABcAFwAXABcACsAXAArACoAKgAqACoAKgAqACsAKwBLAEsASwBLAEsASwBLAEsASwBLACsAKwBcAFwAXABcAFAADgAOAA4ADgAeAA4ADgAJAA4ADgANAAkAEwATABMAEwATAAkAHgATAB4AHgAeAAQABAAeAB4AHgAeAB4AHgBLAEsASwBLAEsASwBLAEsASwBLAFAAUABQAFAAUABQAFAAUABQAFAADQAEAB4ABAAeAAQAFgARABYAEQAEAAQAUABQAFAAUABQAFAAUABQACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwArACsAKwAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQADQAEAAQABAAEAAQADQAEAAQAUABQAFAAUABQAAQABAAEAAQABAAEAAQABAAEAAQABAArAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAArAA0ADQAeAB4AHgAeAB4AHgAEAB4AHgAeAB4AHgAeACsAHgAeAA4ADgANAA4AHgAeAB4AHgAeAAkACQArACsAKwArACsAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcACoAKgAqACoAKgAqACoAKgAqACoAKgAqACoAKgAqACoAKgAqACoAKgBcAEsASwBLAEsASwBLAEsASwBLAEsADQANAB4AHgAeAB4AXABcAFwAXABcAFwAKgAqACoAKgBcAFwAXABcACoAKgAqAFwAKgAqACoAXABcACoAKgAqACoAKgAqACoAXABcAFwAKgAqACoAKgBcAFwAXABcAFwAXABcAFwAXABcAFwAXABcACoAKgAqACoAKgAqACoAKgAqACoAKgAqAFwAKgBLAEsASwBLAEsASwBLAEsASwBLACoAKgAqACoAKgAqAFAAUABQAFAAUABQACsAUAArACsAKwArACsAUAArACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAHgBQAFAAUABQAFgAWABYAFgAWABYAFgAWABYAFgAWABYAFgAWABYAFgAWABYAFgAWABYAFgAWABYAFgAWABYAFgAWABYAFgAWABZAFkAWQBZAFkAWQBZAFkAWQBZAFkAWQBZAFkAWQBZAFkAWQBZAFkAWQBZAFkAWQBZAFkAWQBZAFkAWQBZAFkAWgBaAFoAWgBaAFoAWgBaAFoAWgBaAFoAWgBaAFoAWgBaAFoAWgBaAFoAWgBaAFoAWgBaAFoAWgBaAFoAWgBaAFAAUABQAFAAUABQAFAAUABQACsAUABQAFAAUAArACsAUABQAFAAUABQAFAAUAArAFAAKwBQAFAAUABQACsAKwBQAFAAUABQAFAAUABQAFAAUAArAFAAUABQAFAAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArAFAAUABQAFAAKwArAFAAUABQAFAAUABQAFAAKwBQACsAUABQAFAAUAArACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwBQAFAAUABQACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsABAAEAAQAHgANAB4AHgAeAB4AHgAeAB4AUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAHgAeAB4AHgAeAB4AHgAeAB4AHgArACsAKwArACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwBQAFAAUABQAFAAUAArACsADQBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAHgAeAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAANAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAWABEAKwArACsAUABQAFAAUABQAFAAUABQAFAAUABQAA0ADQANAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwBQAFAAUABQAAQABAAEACsAKwArACsAKwArACsAKwArACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAEAAQABAANAA0AKwArACsAKwArACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAABAAEACsAKwArACsAKwArACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwBQAFAAUAArAAQABAArACsAKwArACsAKwArACsAKwArACsAKwBcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAKgAqACoAKgAqACoAKgAqACoAKgAqACoAKgAqACoAKgAqACoAKgAqAA0ADQAVAFwADQAeAA0AGwBcACoAKwArAEsASwBLAEsASwBLAEsASwBLAEsAKwArACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUAArACsAKwArACsAKwAeAB4AEwATAA0ADQAOAB4AEwATAB4ABAAEAAQACQArAEsASwBLAEsASwBLAEsASwBLAEsAKwArACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsAKwArACsAKwArAFAAUABQAFAAUAAEAAQAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAAQAUAArACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsAKwArACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwAEAAQABAAEAAQABAAEAAQABAAEAAQABAArACsAKwArAAQABAAEAAQABAAEAAQABAAEAAQABAAEACsAKwArACsAHgArACsAKwATABMASwBLAEsASwBLAEsASwBLAEsASwBcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXAArACsAXABcAFwAXABcACsAKwArACsAKwArACsAKwArACsAKwBcAFwAXABcAFwAXABcAFwAXABcAFwAXAArACsAKwArAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcACsAKwArACsAKwArAEsASwBLAEsASwBLAEsASwBLAEsAXAArACsAKwAqACoAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAAQABAAEAAQABAArACsAHgAeAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcACoAKgAqACoAKgAqACoAKgAqACoAKwAqACoAKgAqACoAKgAqACoAKgAqACoAKgAqACoAKgAqACoAKgAqACoAKgAqACoAKgAqACoAKgAqACoAKwArAAQASwBLAEsASwBLAEsASwBLAEsASwArACsAKwArACsAKwBLAEsASwBLAEsASwBLAEsASwBLACsAKwArACsAKwArACoAKgAqACoAKgAqACoAXAAqACoAKgAqACoAKgArACsABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsABAAEAAQABAAEAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAAQABAAEAAQABABQAFAAUABQAFAAUABQACsAKwArACsASwBLAEsASwBLAEsASwBLAEsASwANAA0AHgANAA0ADQANAB4AHgAeAB4AHgAeAB4AHgAeAB4ABAAEAAQABAAEAAQABAAEAAQAHgAeAB4AHgAeAB4AHgAeAB4AKwArACsABAAEAAQAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAABAAEAAQABAAEAAQABAAEAAQABAAEAAQABABQAFAASwBLAEsASwBLAEsASwBLAEsASwBQAFAAUABQAFAAUABQAFAABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEACsAKwArACsAKwArACsAKwAeAB4AHgAeAFAAUABQAFAABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEACsAKwArAA0ADQANAA0ADQBLAEsASwBLAEsASwBLAEsASwBLACsAKwArAFAAUABQAEsASwBLAEsASwBLAEsASwBLAEsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAA0ADQBQAFAAUABQAFAAUABQAFAAUAArACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwBQAFAAUAAeAB4AHgAeAB4AHgAeAB4AKwArACsAKwArACsAKwArAAQABAAEAB4ABAAEAAQABAAEAAQABAAEAAQABAAEAAQABABQAFAAUABQAAQAUABQAFAAUABQAFAABABQAFAABAAEAAQAUAArACsAKwArACsABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEACsABAAEAAQABAAEAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AKwArAFAAUABQAFAAUABQACsAKwBQAFAAUABQAFAAUABQAFAAKwBQACsAUAArAFAAKwAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeACsAKwAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgArAB4AHgAeAB4AHgAeAB4AHgBQAB4AHgAeAFAAUABQACsAHgAeAB4AHgAeAB4AHgAeAB4AHgBQAFAAUABQACsAKwAeAB4AHgAeAB4AHgArAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AKwArAFAAUABQACsAHgAeAB4AHgAeAB4AHgAOAB4AKwANAA0ADQANAA0ADQANAAkADQANAA0ACAAEAAsABAAEAA0ACQANAA0ADAAdAB0AHgAXABcAFgAXABcAFwAWABcAHQAdAB4AHgAUABQAFAANAAEAAQAEAAQABAAEAAQACQAaABoAGgAaABoAGgAaABoAHgAXABcAHQAVABUAHgAeAB4AHgAeAB4AGAAWABEAFQAVABUAHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4ADQAeAA0ADQANAA0AHgANAA0ADQAHAB4AHgAeAB4AKwAEAAQABAAEAAQABAAEAAQABAAEAFAAUAArACsATwBQAFAAUABQAFAAHgAeAB4AFgARAE8AUABPAE8ATwBPAFAAUABQAFAAUAAeAB4AHgAWABEAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwArABsAGwAbABsAGwAbABsAGgAbABsAGwAbABsAGwAbABsAGwAbABsAGwAbABsAGgAbABsAGwAbABoAGwAbABoAGwAbABsAGwAbABsAGwAbABsAGwAbABsAGwAbABsAGwAbAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQAHgAeAFAAGgAeAB0AHgBQAB4AGgAeAB4AHgAeAB4AHgAeAB4AHgBPAB4AUAAbAB4AHgBQAFAAUABQAFAAHgAeAB4AHQAdAB4AUAAeAFAAHgBQAB4AUABPAFAAUAAeAB4AHgAeAB4AHgAeAFAAUABQAFAAUAAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAFAAHgBQAFAAUABQAE8ATwBQAFAAUABQAFAATwBQAFAATwBQAE8ATwBPAE8ATwBPAE8ATwBPAE8ATwBPAFAAUABQAFAATwBPAE8ATwBPAE8ATwBPAE8ATwBQAFAAUABQAFAAUABQAFAAUAAeAB4AUABQAFAAUABPAB4AHgArACsAKwArAB0AHQAdAB0AHQAdAB0AHQAdAB0AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB0AHgAdAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAdAB4AHQAdAB4AHgAeAB0AHQAeAB4AHQAeAB4AHgAdAB4AHQAbABsAHgAdAB4AHgAeAB4AHQAeAB4AHQAdAB0AHQAeAB4AHQAeAB0AHgAdAB0AHQAdAB0AHQAeAB0AHgAeAB4AHgAeAB0AHQAdAB0AHgAeAB4AHgAdAB0AHgAeAB4AHgAeAB4AHgAeAB4AHgAdAB4AHgAeAB0AHgAeAB4AHgAeAB0AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAdAB0AHgAeAB0AHQAdAB0AHgAeAB0AHQAeAB4AHQAdAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB0AHQAeAB4AHQAdAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHQAeAB4AHgAdAB4AHgAeAB4AHgAeAB4AHQAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB0AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AFAAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeABYAEQAWABEAHgAeAB4AHgAeAB4AHQAeAB4AHgAeAB4AHgAeACUAJQAeAB4AHgAeAB4AHgAeAB4AHgAWABEAHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AJQAlACUAJQAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArAE8ATwBPAE8ATwBPAE8ATwBPAE8ATwBPAE8ATwBPAE8ATwBPAE8ATwBPAE8ATwBPAE8ATwBPAE8ATwBPAE8ATwAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAE8ATwBPAE8ATwBPAE8ATwBPAE8ATwBPAE8ATwBPAE8ATwBPAE8ATwBPAFAAHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHgAeAB4AHgAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAeAB4AHQAdAB0AHQAeAB4AHgAeAB4AHgAeAB4AHgAeAB0AHQAeAB0AHQAdAB0AHQAdAB0AHgAeAB4AHgAeAB4AHgAeAB0AHQAeAB4AHQAdAB4AHgAeAB4AHQAdAB4AHgAeAB4AHQAdAB0AHgAeAB0AHgAeAB0AHQAdAB0AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAdAB0AHQAdAB4AHgAeAB4AHgAeAB4AHgAeAB0AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAlACUAJQAlAB4AHQAdAB4AHgAdAB4AHgAeAB4AHQAdAB4AHgAeAB4AJQAlAB0AHQAlAB4AJQAlACUAIAAlACUAHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAlACUAJQAeAB4AHgAeAB0AHgAdAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAdAB0AHgAdAB0AHQAeAB0AJQAdAB0AHgAdAB0AHgAdAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeACUAHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHQAdAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAlACUAJQAlACUAJQAlACUAJQAlACUAJQAdAB0AHQAdACUAHgAlACUAJQAdACUAJQAdAB0AHQAlACUAHQAdACUAHQAdACUAJQAlAB4AHQAeAB4AHgAeAB0AHQAlAB0AHQAdAB0AHQAdACUAJQAlACUAJQAdACUAJQAgACUAHQAdACUAJQAlACUAJQAlACUAJQAeAB4AHgAlACUAIAAgACAAIAAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB0AHgAeAB4AFwAXABcAFwAXABcAHgATABMAJQAeAB4AHgAWABEAFgARABYAEQAWABEAFgARABYAEQAWABEATwBPAE8ATwBPAE8ATwBPAE8ATwBPAE8ATwBPAE8ATwBPAE8ATwBPAE8ATwAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeABYAEQAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAWABEAFgARABYAEQAWABEAFgARAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AFgARABYAEQAWABEAFgARABYAEQAWABEAFgARABYAEQAWABEAFgARABYAEQAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAWABEAFgARAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AFgARAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAdAB0AHQAdAB0AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgArACsAHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AKwAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AUABQAFAAUAAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAEAAQABAAeAB4AKwArACsAKwArABMADQANAA0AUAATAA0AUABQAFAAUABQAFAAUABQACsAKwArACsAKwArACsAUAANACsAKwArACsAKwArACsAKwArACsAKwArACsAKwAEAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsAKwArACsAKwArACsAKwBQAFAAUABQAFAAUABQACsAUABQAFAAUABQAFAAUAArAFAAUABQAFAAUABQAFAAKwBQAFAAUABQAFAAUABQACsAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXAA0ADQANAA0ADQANAA0ADQAeAA0AFgANAB4AHgAXABcAHgAeABcAFwAWABEAFgARABYAEQAWABEADQANAA0ADQATAFAADQANAB4ADQANAB4AHgAeAB4AHgAMAAwADQANAA0AHgANAA0AFgANAA0ADQANAA0ADQANAA0AHgANAB4ADQANAB4AHgAeACsAKwArACsAKwArACsAKwArACsAKwArACsAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACsAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAKwArACsAKwArACsAKwArACsAKwArACsAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwAlACUAJQAlACUAJQAlACUAJQAlACUAJQArACsAKwArAA0AEQARACUAJQBHAFcAVwAWABEAFgARABYAEQAWABEAFgARACUAJQAWABEAFgARABYAEQAWABEAFQAWABEAEQAlAFcAVwBXAFcAVwBXAFcAVwBXAAQABAAEAAQABAAEACUAVwBXAFcAVwA2ACUAJQBXAFcAVwBHAEcAJQAlACUAKwBRAFcAUQBXAFEAVwBRAFcAUQBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFEAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBRAFcAUQBXAFEAVwBXAFcAVwBXAFcAUQBXAFcAVwBXAFcAVwBRAFEAKwArAAQABAAVABUARwBHAFcAFQBRAFcAUQBXAFEAVwBRAFcAUQBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFEAVwBRAFcAUQBXAFcAVwBXAFcAVwBRAFcAVwBXAFcAVwBXAFEAUQBXAFcAVwBXABUAUQBHAEcAVwArACsAKwArACsAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAKwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAKwAlACUAVwBXAFcAVwAlACUAJQAlACUAJQAlACUAJQAlACsAKwArACsAKwArACsAKwArACsAKwArAFEAUQBRAFEAUQBRAFEAUQBRAFEAUQBRAFEAUQBRAFEAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQArAFcAVwBXAFcAVwBXAFcAVwBXAFcAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQBPAE8ATwBPAE8ATwBPAE8AJQBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXACUAJQAlAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAEcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAKwArACsAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQArACsAKwArACsAKwArACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAADQATAA0AUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABLAEsASwBLAEsASwBLAEsASwBLAFAAUAArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAFAABAAEAAQABAAeAAQABAAEAAQABAAEAAQABAAEAAQAHgBQAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AUABQAAQABABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAAQABAAeAA0ADQANAA0ADQArACsAKwArACsAKwArACsAHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAFAAUABQAFAAUABQAFAAUABQAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AUAAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgBQAB4AHgAeAB4AHgAeAFAAHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgArACsAHgAeAB4AHgAeAB4AHgAeAB4AKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwAeAB4AUABQAFAAUABQAFAAUABQAFAAUABQAAQAUABQAFAABABQAFAAUABQAAQAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAAQABAAEAAQABAAeAB4AHgAeAAQAKwArACsAUABQAFAAUABQAFAAHgAeABoAHgArACsAKwArACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAADgAOABMAEwArACsAKwArACsAKwArACsABAAEAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAAQABAAEAAQABAAEACsAKwArACsAKwArACsAKwANAA0ASwBLAEsASwBLAEsASwBLAEsASwArACsAKwArACsAKwAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABABQAFAAUABQAFAAUAAeAB4AHgBQAA4AUABQAAQAUABQAFAAUABQAFAABAAEAAQABAAEAAQABAAEAA0ADQBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQAKwArACsAKwArACsAKwArACsAKwArAB4AWABYAFgAWABYAFgAWABYAFgAWABYAFgAWABYAFgAWABYAFgAWABYAFgAWABYAFgAWABYAFgAWABYACsAKwArAAQAHgAeAB4AHgAeAB4ADQANAA0AHgAeAB4AHgArAFAASwBLAEsASwBLAEsASwBLAEsASwArACsAKwArAB4AHgBcAFwAXABcAFwAKgBcAFwAXABcAFwAXABcAFwAXABcAEsASwBLAEsASwBLAEsASwBLAEsAXABcAFwAXABcACsAUABQAFAAUABQAFAAUABQAFAABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEACsAKwArACsAKwArACsAKwArAFAAUABQAAQAUABQAFAAUABQAFAAUABQAAQABAArACsASwBLAEsASwBLAEsASwBLAEsASwArACsAHgANAA0ADQBcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAKgAqACoAXAAqACoAKgBcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXAAqAFwAKgAqACoAXABcACoAKgBcAFwAXABcAFwAKgAqAFwAKgBcACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArAFwAXABcACoAKgBQAFAAUABQAFAAUABQAFAAUABQAFAABAAEAAQABAAEAA0ADQBQAFAAUAAEAAQAKwArACsAKwArACsAKwArACsAKwBQAFAAUABQAFAAUAArACsAUABQAFAAUABQAFAAKwArAFAAUABQAFAAUABQACsAKwArACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAKwBQAFAAUABQAFAAUABQACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAHgAeACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAEAAQABAAEAAQABAAEAAQADQAEAAQAKwArAEsASwBLAEsASwBLAEsASwBLAEsAKwArACsAKwArACsAVABVAFUAVQBVAFUAVQBVAFUAVQBVAFUAVQBVAFUAVQBVAFUAVQBVAFUAVQBVAFUAVQBVAFUAVQBUAFUAVQBVAFUAVQBVAFUAVQBVAFUAVQBVAFUAVQBVAFUAVQBVAFUAVQBVAFUAVQBVAFUAVQBVACsAKwArACsAKwArACsAKwArACsAKwArAFkAWQBZAFkAWQBZAFkAWQBZAFkAWQBZAFkAWQBZAFkAWQBZAFkAKwArACsAKwBaAFoAWgBaAFoAWgBaAFoAWgBaAFoAWgBaAFoAWgBaAFoAWgBaAFoAWgBaAFoAWgBaAFoAWgBaAFoAKwArACsAKwAGAAYABgAGAAYABgAGAAYABgAGAAYABgAGAAYABgAGAAYABgAGAAYABgAGAAYABgAGAAYABgAGAAYABgAGAAYAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXACUAJQBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAJQAlACUAJQAlACUAUABQAFAAUABQAFAAUAArACsAKwArACsAKwArACsAKwArACsAKwBQAFAAUABQAFAAKwArACsAKwArAFYABABWAFYAVgBWAFYAVgBWAFYAVgBWAB4AVgBWAFYAVgBWAFYAVgBWAFYAVgBWAFYAVgArAFYAVgBWAFYAVgArAFYAKwBWAFYAKwBWAFYAKwBWAFYAVgBWAFYAVgBWAFYAVgBWAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAEQAWAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUAAaAB4AKwArAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQAGAARABEAGAAYABMAEwAWABEAFAArACsAKwArACsAKwAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEACUAJQAlACUAJQAWABEAFgARABYAEQAWABEAFgARABYAEQAlACUAFgARACUAJQAlACUAJQAlACUAEQAlABEAKwAVABUAEwATACUAFgARABYAEQAWABEAJQAlACUAJQAlACUAJQAlACsAJQAbABoAJQArACsAKwArAFAAUABQAFAAUAArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwArAAcAKwATACUAJQAbABoAJQAlABYAEQAlACUAEQAlABEAJQBXAFcAVwBXAFcAVwBXAFcAVwBXABUAFQAlACUAJQATACUAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXABYAJQARACUAJQAlAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwAWACUAEQAlABYAEQARABYAEQARABUAVwBRAFEAUQBRAFEAUQBRAFEAUQBRAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAEcARwArACsAVwBXAFcAVwBXAFcAKwArAFcAVwBXAFcAVwBXACsAKwBXAFcAVwBXAFcAVwArACsAVwBXAFcAKwArACsAGgAbACUAJQAlABsAGwArAB4AHgAeAB4AHgAeAB4AKwArACsAKwArACsAKwArACsAKwAEAAQABAAQAB0AKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwBQAFAAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsAKwArACsADQANAA0AKwArACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwArAB4AHgAeAB4AHgAeAB4AHgAeAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgBQAFAAHgAeAB4AKwAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAAQAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwAEAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwArACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAABAAEAAQABAAEACsAKwArACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArAA0AUABQAFAAUAArACsAKwArAFAAUABQAFAAUABQAFAAUAANAFAAUABQAFAAUAArACsAKwArACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwArACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwArACsAKwArACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwArACsAKwArACsAKwArACsAKwAeACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAUABQAFAAUABQAFAAKwArAFAAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArAFAAUAArACsAKwBQACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwANAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAeAB4AUABQAFAAUABQAFAAUAArACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArAFAAUAArACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwArAA0AUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwArACsAKwAeAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwArACsAUABQAFAAUABQAAQABAAEACsABAAEACsAKwArACsAKwAEAAQABAAEAFAAUABQAFAAKwBQAFAAUAArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwArAAQABAAEACsAKwArACsABABQAFAAUABQAFAAUABQAFAAUAArACsAKwArACsAKwArAA0ADQANAA0ADQANAA0ADQAeACsAKwArACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAeAFAAUABQAFAAUABQAFAAUAAeAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAAQABAArACsAKwArAFAAUABQAFAAUAANAA0ADQANAA0ADQAUACsAKwArACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwArACsADQANAA0ADQANAA0ADQBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsAKwArACsAKwArAB4AHgAeAB4AKwArACsAKwArACsAKwArACsAKwArACsAUABQAFAAUABQAFAAUAArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwArACsAKwArACsAKwArACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsAKwArACsAKwArAFAAUABQAFAAUABQAAQABAAEAAQAKwArACsAKwArACsAKwArAEsASwBLAEsASwBLAEsASwBLAEsAKwArACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUAArAAQABAANACsAKwBQAFAAKwArACsAKwArACsAKwArACsAKwArACsAKwArAFAAUABQAFAAUABQAAQABAAEAAQABAAEAAQABAAEAAQABABQAFAAUABQAB4AHgAeAB4AHgArACsAKwArACsAKwAEAAQABAAEAAQABAAEAA0ADQAeAB4AHgAeAB4AKwArACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAEsASwBLAEsASwBLAEsASwBLAEsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsABABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAAQABAAEAAQABAAEAAQABAAEAAQABAAeAB4AHgANAA0ADQANACsAKwArACsAKwArACsAKwArACsAKwAeACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwArACsAKwArACsAKwBLAEsASwBLAEsASwBLAEsASwBLACsAKwArACsAKwArAFAAUABQAFAAUABQAFAABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEACsASwBLAEsASwBLAEsASwBLAEsASwANAA0ADQANAFAABAAEAFAAKwArACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAABAAeAA4AUAArACsAKwArACsAKwArACsAKwAEAFAAUABQAFAADQANAB4ADQAEAAQABAAEAB4ABAAEAEsASwBLAEsASwBLAEsASwBLAEsAUAAOAFAADQANAA0AKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwArACsAKwArACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAEAAQABAAEAAQABAAEAAQABAAEAAQABAANAA0AHgANAA0AHgAEACsAUABQAFAAUABQAFAAUAArAFAAKwBQAFAAUABQACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwBQAFAAUABQAFAAUABQAFAAUABQAA0AKwArACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAEAAQABAAEAAQABAAEAAQABAAEAAQAKwArACsAKwArAEsASwBLAEsASwBLAEsASwBLAEsAKwArACsAKwArACsABAAEAAQABAArAFAAUABQAFAAUABQAFAAUAArACsAUABQACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwBQAFAAUABQAFAAUABQACsAUABQACsAUABQAFAAUABQACsABAAEAFAABAAEAAQABAAEAAQABAArACsABAAEACsAKwAEAAQABAArACsAUAArACsAKwArACsAKwAEACsAKwArACsAKwBQAFAAUABQAFAABAAEACsAKwAEAAQABAAEAAQABAAEACsAKwArAAQABAAEAAQABAArACsAKwArACsAKwArACsAKwArACsABAAEAAQABAAEAAQABABQAFAAUABQAA0ADQANAA0AHgBLAEsASwBLAEsASwBLAEsASwBLAA0ADQArAB4ABABQAFAAUAArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwAEAAQABAAEAFAAUAAeAFAAKwArACsAKwArACsAKwArAEsASwBLAEsASwBLAEsASwBLAEsAKwArACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAABAAEAAQABAAEAAQABAArACsABAAEAAQABAAEAAQABAAEAAQADgANAA0AEwATAB4AHgAeAA0ADQANAA0ADQANAA0ADQANAA0ADQANAA0ADQANAFAAUABQAFAABAAEACsAKwAEAA0ADQAeAFAAKwArACsAKwArACsAKwArACsAKwArAEsASwBLAEsASwBLAEsASwBLAEsAKwArACsAKwArACsADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAFAAKwArACsAKwArACsAKwBLAEsASwBLAEsASwBLAEsASwBLACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAXABcAFwAKwArACoAKgAqACoAKgAqACoAKgAqACoAKgAqACoAKgAqACsAKwArACsASwBLAEsASwBLAEsASwBLAEsASwBcAFwADQANAA0AKgBQAFAAUABQAFAAUABQAFAAUABQAFAAUAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAeACsAKwArACsASwBLAEsASwBLAEsASwBLAEsASwBQAFAAUABQAFAAUABQAFAAUAArACsAKwArACsAKwArACsAKwArACsAKwBQAFAAUABQAFAAUABQAFAAKwArAFAAKwArAFAAUABQAFAAUABQAFAAUAArAFAAUAArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAABAAEAAQABAAEAAQAKwAEAAQAKwArAAQABAAEAAQAUAAEAFAABAAEAA0ADQANACsAKwArACsAKwArACsAKwArAEsASwBLAEsASwBLAEsASwBLAEsAKwArACsAKwArACsAUABQAFAAUABQAFAAUABQACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAABAAEAAQABAAEAAQABAArACsABAAEAAQABAAEAAQABABQAA4AUAAEACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArAFAABAAEAAQABAAEAAQABAAEAAQABABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAEAAQABAAEAAQABAAEAFAABAAEAAQABAAOAB4ADQANAA0ADQAOAB4ABAArACsAKwArACsAKwArACsAUAAEAAQABAAEAAQABAAEAAQABAAEAAQAUABQAFAAUABQAFAAUABQAFAAUAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAA0ADQANAFAADgAOAA4ADQANACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwBQAFAAUABQAFAAUABQAFAAUAArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAABAAEAAQABAAEAAQABAAEACsABAAEAAQABAAEAAQABAAEAFAADQANAA0ADQANACsAKwArACsAKwArACsAKwArACsASwBLAEsASwBLAEsASwBLAEsASwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsAKwAOABMAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwArAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAArAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAArACsAKwArACsAKwArACsAKwBQAFAAUABQAFAAUABQACsAUABQACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAEAAQABAAEAAQABAArACsAKwAEACsABAAEACsABAAEAAQABAAEAAQABABQAAQAKwArACsAKwArACsAKwArAEsASwBLAEsASwBLAEsASwBLAEsAKwArACsAKwArACsAUABQAFAAUABQAFAAKwBQAFAAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAEAAQABAAEAAQAKwAEAAQAKwAEAAQABAAEAAQAUAArACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAABAAEAAQABAAeAB4AKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwBQACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAB4AHgAeAB4AHgAeAB4AHgAaABoAGgAaAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgArACsAKwArACsAKwArACsAKwArACsAKwArAA0AUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsADQANAA0ADQANACsAKwArACsAKwArACsAKwArACsAKwBQAFAAUABQACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAASABIAEgAQwBDAEMAUABQAFAAUABDAFAAUABQAEgAQwBIAEMAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAASABDAEMAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwAJAAkACQAJAAkACQAJABYAEQArACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABIAEMAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArAEsASwBLAEsASwBLAEsASwBLAEsAKwArACsAKwANAA0AKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwArAAQABAAEAAQABAANACsAKwArACsAKwArACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAEAAQABAAEAAQABAAEAA0ADQANAB4AHgAeAB4AHgAeAFAAUABQAFAADQAeACsAKwArACsAKwArACsAKwArACsASwBLAEsASwBLAEsASwBLAEsASwArAFAAUABQAFAAUABQAFAAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAANAA0AHgAeACsAKwArACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAKwArACsAKwAEAFAABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQAKwArACsAKwArACsAKwAEAAQABAAEAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAARwBHABUARwAJACsAKwArACsAKwArACsAKwArACsAKwAEAAQAKwArACsAKwArACsAKwArACsAKwArACsAKwArAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXACsAKwArACsAKwArACsAKwBXAFcAVwBXAFcAVwBXAFcAVwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAUQBRAFEAKwArACsAKwArACsAKwArACsAKwArACsAKwBRAFEAUQBRACsAKwArACsAKwArACsAKwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwArACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwArACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUAArACsAHgAEAAQADQAEAAQABAAEACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgArACsAKwArACsAKwArACsAKwArAB4AHgAeAB4AHgAeAB4AKwArAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAAQABAAEAAQABAAeAB4AHgAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAB4AHgAEAAQABAAEAAQABAAEAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4ABAAEAAQABAAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4ABAAEAAQAHgArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwArACsAKwArACsAKwArACsAKwArAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgArACsAKwArACsAKwArACsAKwAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgArAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AKwBQAFAAKwArAFAAKwArAFAAUAArACsAUABQAFAAUAArAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeACsAUAArAFAAUABQAFAAUABQAFAAKwAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AKwBQAFAAUABQACsAKwBQAFAAUABQAFAAUABQAFAAKwBQAFAAUABQAFAAUABQACsAHgAeAFAAUABQAFAAUAArAFAAKwArACsAUABQAFAAUABQAFAAUAArAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAHgBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgBQAFAAUABQAFAAUABQAFAAUABQAFAAHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAB4AHgAeAB4AHgAeAB4AHgAeACsAKwBLAEsASwBLAEsASwBLAEsASwBLAEsASwBLAEsASwBLAEsASwBLAEsASwBLAEsASwBLAEsASwBLAEsASwBLAEsASwBLAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAeAB4AHgAeAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAeAB4AHgAeAB4AHgAeAB4ABAAeAB4AHgAeAB4AHgAeAB4AHgAeAAQAHgAeAA0ADQANAA0AHgArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwAEAAQABAAEAAQAKwAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArAAQABAAEAAQABAAEAAQAKwAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQAKwArAAQABAAEAAQABAAEAAQAKwAEAAQAKwAEAAQABAAEAAQAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsAKwAEAAQABAAEAAQABAAEAFAAUABQAFAAUABQAFAAKwArAEsASwBLAEsASwBLAEsASwBLAEsAKwArACsAKwBQAB4AKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUAAEAAQABAAEAEsASwBLAEsASwBLAEsASwBLAEsAKwArACsAKwArABsAUABQAFAAUABQACsAKwBQAFAAUABQAFAAUABQAFAAUAAEAAQABAAEAAQABAAEACsAKwArACsAKwArACsAKwArAB4AHgAeAB4ABAAEAAQABAAEAAQABABQACsAKwArACsASwBLAEsASwBLAEsASwBLAEsASwArACsAKwArABYAFgArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAGgBQAFAAUAAaAFAAUABQAFAAKwArACsAKwArACsAKwArACsAKwArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAeAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQACsAKwBQAFAAUABQACsAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwBQAFAAKwBQACsAKwBQACsAUABQAFAAUABQAFAAUABQAFAAUAArAFAAUABQAFAAKwBQACsAUAArACsAKwArACsAKwBQACsAKwArACsAUAArAFAAKwBQACsAUABQAFAAKwBQAFAAKwBQACsAKwBQACsAUAArAFAAKwBQACsAUAArAFAAUAArAFAAKwArAFAAUABQAFAAKwBQAFAAUABQAFAAUABQACsAUABQAFAAUAArAFAAUABQAFAAKwBQACsAUABQAFAAUABQAFAAUABQAFAAUAArAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAArACsAKwArACsAUABQAFAAKwBQAFAAUABQAFAAKwBQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwAeAB4AKwArACsAKwArACsAKwArACsAKwArACsAKwArAE8ATwBPAE8ATwBPAE8ATwBPAE8ATwBPAE8AJQAlACUAHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHgAeAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB4AHgAeACUAJQAlAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAdAB0AHQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQApACkAKQApACkAKQApACkAKQApACkAKQApACkAKQApACkAKQApACkAKQApACkAKQApACkAJQAlACUAJQAlACAAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAeAB4AJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlAB4AHgAlACUAJQAlACUAHgAlACUAJQAlACUAIAAgACAAJQAlACAAJQAlACAAIAAgACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACEAIQAhACEAIQAlACUAIAAgACUAJQAgACAAIAAgACAAIAAgACAAIAAgACAAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAJQAlACUAIAAlACUAJQAlACAAIAAgACUAIAAgACAAJQAlACUAJQAlACUAJQAgACUAIAAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAHgAlAB4AJQAeACUAJQAlACUAJQAgACUAJQAlACUAHgAlAB4AHgAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlAB4AHgAeAB4AHgAeAB4AJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAeAB4AHgAeAB4AHgAeAB4AHgAeACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACAAIAAlACUAJQAlACAAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACAAJQAlACUAJQAgACAAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAHgAeAB4AHgAeAB4AHgAeACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAeAB4AHgAeAB4AHgAlACUAJQAlACUAJQAlACAAIAAgACUAJQAlACAAIAAgACAAIAAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeABcAFwAXABUAFQAVAB4AHgAeAB4AJQAlACUAIAAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACAAIAAgACUAJQAlACUAJQAlACUAJQAlACAAJQAlACUAJQAlACUAJQAlACUAJQAlACAAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AJQAlACUAJQAlACUAJQAlACUAJQAlACUAHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AJQAlACUAJQAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeACUAJQAlACUAJQAlACUAJQAeAB4AHgAeAB4AHgAeAB4AHgAeACUAJQAlACUAJQAlAB4AHgAeAB4AHgAeAB4AHgAlACUAJQAlACUAJQAlACUAHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAgACUAJQAgACUAJQAlACUAJQAlACUAJQAgACAAIAAgACAAIAAgACAAJQAlACUAJQAlACUAIAAlACUAJQAlACUAJQAlACUAJQAgACAAIAAgACAAIAAgACAAIAAgACUAJQAgACAAIAAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAgACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACAAIAAlACAAIAAlACAAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAgACAAIAAlACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAJQAlAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AKwAeAB4AHgAeAB4AHgAeAB4AHgAeAB4AHgArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArAEsASwBLAEsASwBLAEsASwBLAEsAKwArACsAKwArACsAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAKwArAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXACUAJQBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwAlACUAJQAlACUAJQAlACUAJQAlACUAVwBXACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQBXAFcAVwBXAFcAVwBXAFcAVwBXAFcAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAJQAlACUAKwAEACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArACsAKwArAA==",
    br = 50,
    fB = 1,
    Dn = 2,
    Sn = 3,
    CB = 4,
    hB = 5,
    xr = 7,
    Tn = 8,
    Dr = 9,
    EA = 10,
    Xt = 11,
    Sr = 12,
    Jt = 13,
    UB = 14,
    Be = 15,
    Yt = 16,
    Le = 17,
    ee = 18,
    FB = 19,
    Tr = 20,
    Wt = 21,
    te = 22,
    Ht = 23,
    VA = 24,
    z = 25,
    ie = 26,
    ae = 27,
    kA = 28,
    dB = 29,
    OA = 30,
    pB = 31,
    Ke = 32,
    be = 33,
    Zt = 34,
    qt = 35,
    jt = 36,
    Ce = 37,
    zt = 38,
    Ze = 39,
    qe = 40,
    vt = 41,
    On = 42,
    EB = 43,
    HB = [9001, 65288],
    Mn = "!",
    I = "×",
    xe = "÷",
    $t = gB(wB),
    uA = [OA, jt],
    Ar = [fB, Dn, Sn, hB],
    Rn = [EA, Tn],
    Or = [ae, ie],
    vB = Ar.concat(Rn),
    Mr = [zt, Ze, qe, Zt, qt],
    IB = [Be, Jt],
    mB = function (e, A) {
        A === void 0 && (A = "strict");
        var t = [],
            r = [],
            n = [];
        return (
            e.forEach(function (s, B) {
                var i = $t.get(s);
                if (
                    (i > br ? (n.push(!0), (i -= br)) : n.push(!1),
                    ["normal", "auto", "loose"].indexOf(A) !== -1 && [8208, 8211, 12316, 12448].indexOf(s) !== -1)
                )
                    return r.push(B), t.push(Yt);
                if (i === CB || i === Xt) {
                    if (B === 0) return r.push(B), t.push(OA);
                    var a = t[B - 1];
                    return vB.indexOf(a) === -1 ? (r.push(r[B - 1]), t.push(a)) : (r.push(B), t.push(OA));
                }
                if ((r.push(B), i === pB)) return t.push(A === "strict" ? Wt : Ce);
                if (i === On || i === dB) return t.push(OA);
                if (i === EB)
                    return (s >= 131072 && s <= 196605) || (s >= 196608 && s <= 262141) ? t.push(Ce) : t.push(OA);
                t.push(i);
            }),
            [r, t, n]
        );
    },
    It = function (e, A, t, r) {
        var n = r[t];
        if (Array.isArray(e) ? e.indexOf(n) !== -1 : e === n)
            for (var s = t; s <= r.length; ) {
                s++;
                var B = r[s];
                if (B === A) return !0;
                if (B !== EA) break;
            }
        if (n === EA)
            for (var s = t; s > 0; ) {
                s--;
                var i = r[s];
                if (Array.isArray(e) ? e.indexOf(i) !== -1 : e === i)
                    for (var a = t; a <= r.length; ) {
                        a++;
                        var B = r[a];
                        if (B === A) return !0;
                        if (B !== EA) break;
                    }
                if (i !== EA) break;
            }
        return !1;
    },
    Rr = function (e, A) {
        for (var t = e; t >= 0; ) {
            var r = A[t];
            if (r === EA) t--;
            else return r;
        }
        return 0;
    },
    yB = function (e, A, t, r, n) {
        if (t[r] === 0) return I;
        var s = r - 1;
        if (Array.isArray(n) && n[s] === !0) return I;
        var B = s - 1,
            i = s + 1,
            a = A[s],
            o = B >= 0 ? A[B] : 0,
            c = A[i];
        if (a === Dn && c === Sn) return I;
        if (Ar.indexOf(a) !== -1) return Mn;
        if (Ar.indexOf(c) !== -1 || Rn.indexOf(c) !== -1) return I;
        if (Rr(s, A) === Tn) return xe;
        if (
            $t.get(e[s]) === Xt ||
            ((a === Ke || a === be) && $t.get(e[i]) === Xt) ||
            a === xr ||
            c === xr ||
            a === Dr ||
            ([EA, Jt, Be].indexOf(a) === -1 && c === Dr) ||
            [Le, ee, FB, VA, kA].indexOf(c) !== -1 ||
            Rr(s, A) === te ||
            It(Ht, te, s, A) ||
            It([Le, ee], Wt, s, A) ||
            It(Sr, Sr, s, A)
        )
            return I;
        if (a === EA) return xe;
        if (a === Ht || c === Ht) return I;
        if (c === Yt || a === Yt) return xe;
        if (
            [Jt, Be, Wt].indexOf(c) !== -1 ||
            a === UB ||
            (o === jt && IB.indexOf(a) !== -1) ||
            (a === kA && c === jt) ||
            c === Tr ||
            (uA.indexOf(c) !== -1 && a === z) ||
            (uA.indexOf(a) !== -1 && c === z) ||
            (a === ae && [Ce, Ke, be].indexOf(c) !== -1) ||
            ([Ce, Ke, be].indexOf(a) !== -1 && c === ie) ||
            (uA.indexOf(a) !== -1 && Or.indexOf(c) !== -1) ||
            (Or.indexOf(a) !== -1 && uA.indexOf(c) !== -1) ||
            ([ae, ie].indexOf(a) !== -1 && (c === z || ([te, Be].indexOf(c) !== -1 && A[i + 1] === z))) ||
            ([te, Be].indexOf(a) !== -1 && c === z) ||
            (a === z && [z, kA, VA].indexOf(c) !== -1)
        )
            return I;
        if ([z, kA, VA, Le, ee].indexOf(c) !== -1)
            for (var l = s; l >= 0; ) {
                var g = A[l];
                if (g === z) return I;
                if ([kA, VA].indexOf(g) !== -1) l--;
                else break;
            }
        if ([ae, ie].indexOf(c) !== -1)
            for (var l = [Le, ee].indexOf(a) !== -1 ? B : s; l >= 0; ) {
                var g = A[l];
                if (g === z) return I;
                if ([kA, VA].indexOf(g) !== -1) l--;
                else break;
            }
        if (
            (zt === a && [zt, Ze, Zt, qt].indexOf(c) !== -1) ||
            ([Ze, Zt].indexOf(a) !== -1 && [Ze, qe].indexOf(c) !== -1) ||
            ([qe, qt].indexOf(a) !== -1 && c === qe) ||
            (Mr.indexOf(a) !== -1 && [Tr, ie].indexOf(c) !== -1) ||
            (Mr.indexOf(c) !== -1 && a === ae) ||
            (uA.indexOf(a) !== -1 && uA.indexOf(c) !== -1) ||
            (a === VA && uA.indexOf(c) !== -1) ||
            (uA.concat(z).indexOf(a) !== -1 && c === te && HB.indexOf(e[i]) === -1) ||
            (uA.concat(z).indexOf(c) !== -1 && a === ee)
        )
            return I;
        if (a === vt && c === vt) {
            for (var w = t[s], Q = 1; w > 0 && (w--, A[w] === vt); ) Q++;
            if (Q % 2 !== 0) return I;
        }
        return a === Ke && c === be ? I : xe;
    },
    LB = function (e, A) {
        A || (A = { lineBreak: "normal", wordBreak: "normal" });
        var t = mB(e, A.lineBreak),
            r = t[0],
            n = t[1],
            s = t[2];
        (A.wordBreak === "break-all" || A.wordBreak === "break-word") &&
            (n = n.map(function (i) {
                return [z, OA, On].indexOf(i) !== -1 ? Ce : i;
            }));
        var B =
            A.wordBreak === "keep-all"
                ? s.map(function (i, a) {
                      return i && e[a] >= 19968 && e[a] <= 40959;
                  })
                : void 0;
        return [r, n, B];
    },
    KB = (function () {
        function e(A, t, r, n) {
            (this.codePoints = A), (this.required = t === Mn), (this.start = r), (this.end = n);
        }
        return (
            (e.prototype.slice = function () {
                return O.apply(void 0, this.codePoints.slice(this.start, this.end));
            }),
            e
        );
    })(),
    bB = function (e, A) {
        var t = gt(e),
            r = LB(t, A),
            n = r[0],
            s = r[1],
            B = r[2],
            i = t.length,
            a = 0,
            o = 0;
        return {
            next: function () {
                if (o >= i) return { done: !0, value: null };
                for (var c = I; o < i && (c = yB(t, s, n, ++o, B)) === I; );
                if (c !== I || o === i) {
                    var l = new KB(t, c, a, o);
                    return (a = o), { value: l, done: !1 };
                }
                return { done: !0, value: null };
            },
        };
    },
    xB = 1 << 0,
    DB = 1 << 1,
    Fe = 1 << 2,
    Nr = 1 << 3,
    At = 10,
    Gr = 47,
    ge = 92,
    SB = 9,
    TB = 32,
    De = 34,
    re = 61,
    OB = 35,
    MB = 36,
    RB = 37,
    Se = 39,
    Te = 40,
    ne = 41,
    NB = 95,
    q = 45,
    GB = 33,
    VB = 60,
    kB = 62,
    PB = 64,
    _B = 91,
    XB = 93,
    JB = 61,
    YB = 123,
    Oe = 63,
    WB = 125,
    Vr = 124,
    ZB = 126,
    qB = 128,
    kr = 65533,
    mt = 42,
    MA = 43,
    jB = 44,
    zB = 58,
    $B = 59,
    he = 46,
    Ai = 0,
    ei = 8,
    ti = 11,
    ri = 14,
    ni = 31,
    si = 127,
    iA = -1,
    Nn = 48,
    Gn = 97,
    Vn = 101,
    Bi = 102,
    ii = 117,
    ai = 122,
    kn = 65,
    Pn = 69,
    _n = 70,
    oi = 85,
    ci = 90,
    X = function (e) {
        return e >= Nn && e <= 57;
    },
    li = function (e) {
        return e >= 55296 && e <= 57343;
    },
    PA = function (e) {
        return X(e) || (e >= kn && e <= _n) || (e >= Gn && e <= Bi);
    },
    gi = function (e) {
        return e >= Gn && e <= ai;
    },
    ui = function (e) {
        return e >= kn && e <= ci;
    },
    Qi = function (e) {
        return gi(e) || ui(e);
    },
    wi = function (e) {
        return e >= qB;
    },
    Me = function (e) {
        return e === At || e === SB || e === TB;
    },
    et = function (e) {
        return Qi(e) || wi(e) || e === NB;
    },
    Pr = function (e) {
        return et(e) || X(e) || e === q;
    },
    fi = function (e) {
        return (e >= Ai && e <= ei) || e === ti || (e >= ri && e <= ni) || e === si;
    },
    pA = function (e, A) {
        return e !== ge ? !1 : A !== At;
    },
    Re = function (e, A, t) {
        return e === q ? et(A) || pA(A, t) : et(e) ? !0 : !!(e === ge && pA(e, A));
    },
    yt = function (e, A, t) {
        return e === MA || e === q ? (X(A) ? !0 : A === he && X(t)) : X(e === he ? A : e);
    },
    Ci = function (e) {
        var A = 0,
            t = 1;
        (e[A] === MA || e[A] === q) && (e[A] === q && (t = -1), A++);
        for (var r = []; X(e[A]); ) r.push(e[A++]);
        var n = r.length ? parseInt(O.apply(void 0, r), 10) : 0;
        e[A] === he && A++;
        for (var s = []; X(e[A]); ) s.push(e[A++]);
        var B = s.length,
            i = B ? parseInt(O.apply(void 0, s), 10) : 0;
        (e[A] === Pn || e[A] === Vn) && A++;
        var a = 1;
        (e[A] === MA || e[A] === q) && (e[A] === q && (a = -1), A++);
        for (var o = []; X(e[A]); ) o.push(e[A++]);
        var c = o.length ? parseInt(O.apply(void 0, o), 10) : 0;
        return t * (n + i * Math.pow(10, -B)) * Math.pow(10, a * c);
    },
    hi = { type: 2 },
    Ui = { type: 3 },
    Fi = { type: 4 },
    di = { type: 13 },
    pi = { type: 8 },
    Ei = { type: 21 },
    Hi = { type: 9 },
    vi = { type: 10 },
    Ii = { type: 11 },
    mi = { type: 12 },
    yi = { type: 14 },
    Ne = { type: 23 },
    Li = { type: 1 },
    Ki = { type: 25 },
    bi = { type: 24 },
    xi = { type: 26 },
    Di = { type: 27 },
    Si = { type: 28 },
    Ti = { type: 29 },
    Oi = { type: 31 },
    er = { type: 32 },
    Xn = (function () {
        function e() {
            this._value = [];
        }
        return (
            (e.prototype.write = function (A) {
                this._value = this._value.concat(gt(A));
            }),
            (e.prototype.read = function () {
                for (var A = [], t = this.consumeToken(); t !== er; ) A.push(t), (t = this.consumeToken());
                return A;
            }),
            (e.prototype.consumeToken = function () {
                var A = this.consumeCodePoint();
                switch (A) {
                    case De:
                        return this.consumeStringToken(De);
                    case OB:
                        var t = this.peekCodePoint(0),
                            r = this.peekCodePoint(1),
                            n = this.peekCodePoint(2);
                        if (Pr(t) || pA(r, n)) {
                            var s = Re(t, r, n) ? DB : xB,
                                B = this.consumeName();
                            return { type: 5, value: B, flags: s };
                        }
                        break;
                    case MB:
                        if (this.peekCodePoint(0) === re) return this.consumeCodePoint(), di;
                        break;
                    case Se:
                        return this.consumeStringToken(Se);
                    case Te:
                        return hi;
                    case ne:
                        return Ui;
                    case mt:
                        if (this.peekCodePoint(0) === re) return this.consumeCodePoint(), yi;
                        break;
                    case MA:
                        if (yt(A, this.peekCodePoint(0), this.peekCodePoint(1)))
                            return this.reconsumeCodePoint(A), this.consumeNumericToken();
                        break;
                    case jB:
                        return Fi;
                    case q:
                        var i = A,
                            a = this.peekCodePoint(0),
                            o = this.peekCodePoint(1);
                        if (yt(i, a, o)) return this.reconsumeCodePoint(A), this.consumeNumericToken();
                        if (Re(i, a, o)) return this.reconsumeCodePoint(A), this.consumeIdentLikeToken();
                        if (a === q && o === kB) return this.consumeCodePoint(), this.consumeCodePoint(), bi;
                        break;
                    case he:
                        if (yt(A, this.peekCodePoint(0), this.peekCodePoint(1)))
                            return this.reconsumeCodePoint(A), this.consumeNumericToken();
                        break;
                    case Gr:
                        if (this.peekCodePoint(0) === mt)
                            for (this.consumeCodePoint(); ; ) {
                                var c = this.consumeCodePoint();
                                if (c === mt && ((c = this.consumeCodePoint()), c === Gr)) return this.consumeToken();
                                if (c === iA) return this.consumeToken();
                            }
                        break;
                    case zB:
                        return xi;
                    case $B:
                        return Di;
                    case VB:
                        if (this.peekCodePoint(0) === GB && this.peekCodePoint(1) === q && this.peekCodePoint(2) === q)
                            return this.consumeCodePoint(), this.consumeCodePoint(), Ki;
                        break;
                    case PB:
                        var l = this.peekCodePoint(0),
                            g = this.peekCodePoint(1),
                            w = this.peekCodePoint(2);
                        if (Re(l, g, w)) {
                            var B = this.consumeName();
                            return { type: 7, value: B };
                        }
                        break;
                    case _B:
                        return Si;
                    case ge:
                        if (pA(A, this.peekCodePoint(0)))
                            return this.reconsumeCodePoint(A), this.consumeIdentLikeToken();
                        break;
                    case XB:
                        return Ti;
                    case JB:
                        if (this.peekCodePoint(0) === re) return this.consumeCodePoint(), pi;
                        break;
                    case YB:
                        return Ii;
                    case WB:
                        return mi;
                    case ii:
                    case oi:
                        var Q = this.peekCodePoint(0),
                            f = this.peekCodePoint(1);
                        return (
                            Q === MA &&
                                (PA(f) || f === Oe) &&
                                (this.consumeCodePoint(), this.consumeUnicodeRangeToken()),
                            this.reconsumeCodePoint(A),
                            this.consumeIdentLikeToken()
                        );
                    case Vr:
                        if (this.peekCodePoint(0) === re) return this.consumeCodePoint(), Hi;
                        if (this.peekCodePoint(0) === Vr) return this.consumeCodePoint(), Ei;
                        break;
                    case ZB:
                        if (this.peekCodePoint(0) === re) return this.consumeCodePoint(), vi;
                        break;
                    case iA:
                        return er;
                }
                return Me(A)
                    ? (this.consumeWhiteSpace(), Oi)
                    : X(A)
                    ? (this.reconsumeCodePoint(A), this.consumeNumericToken())
                    : et(A)
                    ? (this.reconsumeCodePoint(A), this.consumeIdentLikeToken())
                    : { type: 6, value: O(A) };
            }),
            (e.prototype.consumeCodePoint = function () {
                var A = this._value.shift();
                return typeof A == "undefined" ? -1 : A;
            }),
            (e.prototype.reconsumeCodePoint = function (A) {
                this._value.unshift(A);
            }),
            (e.prototype.peekCodePoint = function (A) {
                return A >= this._value.length ? -1 : this._value[A];
            }),
            (e.prototype.consumeUnicodeRangeToken = function () {
                for (var A = [], t = this.consumeCodePoint(); PA(t) && A.length < 6; )
                    A.push(t), (t = this.consumeCodePoint());
                for (var r = !1; t === Oe && A.length < 6; ) A.push(t), (t = this.consumeCodePoint()), (r = !0);
                if (r) {
                    var n = parseInt(
                            O.apply(
                                void 0,
                                A.map(function (a) {
                                    return a === Oe ? Nn : a;
                                })
                            ),
                            16
                        ),
                        s = parseInt(
                            O.apply(
                                void 0,
                                A.map(function (a) {
                                    return a === Oe ? _n : a;
                                })
                            ),
                            16
                        );
                    return { type: 30, start: n, end: s };
                }
                var B = parseInt(O.apply(void 0, A), 16);
                if (this.peekCodePoint(0) === q && PA(this.peekCodePoint(1))) {
                    this.consumeCodePoint(), (t = this.consumeCodePoint());
                    for (var i = []; PA(t) && i.length < 6; ) i.push(t), (t = this.consumeCodePoint());
                    var s = parseInt(O.apply(void 0, i), 16);
                    return { type: 30, start: B, end: s };
                } else return { type: 30, start: B, end: B };
            }),
            (e.prototype.consumeIdentLikeToken = function () {
                var A = this.consumeName();
                return A.toLowerCase() === "url" && this.peekCodePoint(0) === Te
                    ? (this.consumeCodePoint(), this.consumeUrlToken())
                    : this.peekCodePoint(0) === Te
                    ? (this.consumeCodePoint(), { type: 19, value: A })
                    : { type: 20, value: A };
            }),
            (e.prototype.consumeUrlToken = function () {
                var A = [];
                if ((this.consumeWhiteSpace(), this.peekCodePoint(0) === iA)) return { type: 22, value: "" };
                var t = this.peekCodePoint(0);
                if (t === Se || t === De) {
                    var r = this.consumeStringToken(this.consumeCodePoint());
                    return r.type === 0 &&
                        (this.consumeWhiteSpace(), this.peekCodePoint(0) === iA || this.peekCodePoint(0) === ne)
                        ? (this.consumeCodePoint(), { type: 22, value: r.value })
                        : (this.consumeBadUrlRemnants(), Ne);
                }
                for (;;) {
                    var n = this.consumeCodePoint();
                    if (n === iA || n === ne) return { type: 22, value: O.apply(void 0, A) };
                    if (Me(n))
                        return (
                            this.consumeWhiteSpace(),
                            this.peekCodePoint(0) === iA || this.peekCodePoint(0) === ne
                                ? (this.consumeCodePoint(), { type: 22, value: O.apply(void 0, A) })
                                : (this.consumeBadUrlRemnants(), Ne)
                        );
                    if (n === De || n === Se || n === Te || fi(n)) return this.consumeBadUrlRemnants(), Ne;
                    if (n === ge)
                        if (pA(n, this.peekCodePoint(0))) A.push(this.consumeEscapedCodePoint());
                        else return this.consumeBadUrlRemnants(), Ne;
                    else A.push(n);
                }
            }),
            (e.prototype.consumeWhiteSpace = function () {
                for (; Me(this.peekCodePoint(0)); ) this.consumeCodePoint();
            }),
            (e.prototype.consumeBadUrlRemnants = function () {
                for (;;) {
                    var A = this.consumeCodePoint();
                    if (A === ne || A === iA) return;
                    pA(A, this.peekCodePoint(0)) && this.consumeEscapedCodePoint();
                }
            }),
            (e.prototype.consumeStringSlice = function (A) {
                for (var t = 5e4, r = ""; A > 0; ) {
                    var n = Math.min(t, A);
                    (r += O.apply(void 0, this._value.splice(0, n))), (A -= n);
                }
                return this._value.shift(), r;
            }),
            (e.prototype.consumeStringToken = function (A) {
                var t = "",
                    r = 0;
                do {
                    var n = this._value[r];
                    if (n === iA || n === void 0 || n === A)
                        return (t += this.consumeStringSlice(r)), { type: 0, value: t };
                    if (n === At) return this._value.splice(0, r), Li;
                    if (n === ge) {
                        var s = this._value[r + 1];
                        s !== iA &&
                            s !== void 0 &&
                            (s === At
                                ? ((t += this.consumeStringSlice(r)), (r = -1), this._value.shift())
                                : pA(n, s) &&
                                  ((t += this.consumeStringSlice(r)),
                                  (t += O(this.consumeEscapedCodePoint())),
                                  (r = -1)));
                    }
                    r++;
                } while (!0);
            }),
            (e.prototype.consumeNumber = function () {
                var A = [],
                    t = Fe,
                    r = this.peekCodePoint(0);
                for ((r === MA || r === q) && A.push(this.consumeCodePoint()); X(this.peekCodePoint(0)); )
                    A.push(this.consumeCodePoint());
                r = this.peekCodePoint(0);
                var n = this.peekCodePoint(1);
                if (r === he && X(n))
                    for (A.push(this.consumeCodePoint(), this.consumeCodePoint()), t = Nr; X(this.peekCodePoint(0)); )
                        A.push(this.consumeCodePoint());
                (r = this.peekCodePoint(0)), (n = this.peekCodePoint(1));
                var s = this.peekCodePoint(2);
                if ((r === Pn || r === Vn) && (((n === MA || n === q) && X(s)) || X(n)))
                    for (A.push(this.consumeCodePoint(), this.consumeCodePoint()), t = Nr; X(this.peekCodePoint(0)); )
                        A.push(this.consumeCodePoint());
                return [Ci(A), t];
            }),
            (e.prototype.consumeNumericToken = function () {
                var A = this.consumeNumber(),
                    t = A[0],
                    r = A[1],
                    n = this.peekCodePoint(0),
                    s = this.peekCodePoint(1),
                    B = this.peekCodePoint(2);
                if (Re(n, s, B)) {
                    var i = this.consumeName();
                    return { type: 15, number: t, flags: r, unit: i };
                }
                return n === RB
                    ? (this.consumeCodePoint(), { type: 16, number: t, flags: r })
                    : { type: 17, number: t, flags: r };
            }),
            (e.prototype.consumeEscapedCodePoint = function () {
                var A = this.consumeCodePoint();
                if (PA(A)) {
                    for (var t = O(A); PA(this.peekCodePoint(0)) && t.length < 6; ) t += O(this.consumeCodePoint());
                    Me(this.peekCodePoint(0)) && this.consumeCodePoint();
                    var r = parseInt(t, 16);
                    return r === 0 || li(r) || r > 1114111 ? kr : r;
                }
                return A === iA ? kr : A;
            }),
            (e.prototype.consumeName = function () {
                for (var A = ""; ; ) {
                    var t = this.consumeCodePoint();
                    if (Pr(t)) A += O(t);
                    else if (pA(t, this.peekCodePoint(0))) A += O(this.consumeEscapedCodePoint());
                    else return this.reconsumeCodePoint(t), A;
                }
            }),
            e
        );
    })(),
    Jn = (function () {
        function e(A) {
            this._tokens = A;
        }
        return (
            (e.create = function (A) {
                var t = new Xn();
                return t.write(A), new e(t.read());
            }),
            (e.parseValue = function (A) {
                return e.create(A).parseComponentValue();
            }),
            (e.parseValues = function (A) {
                return e.create(A).parseComponentValues();
            }),
            (e.prototype.parseComponentValue = function () {
                for (var A = this.consumeToken(); A.type === 31; ) A = this.consumeToken();
                if (A.type === 32) throw new SyntaxError("Error parsing CSS component value, unexpected EOF");
                this.reconsumeToken(A);
                var t = this.consumeComponentValue();
                do A = this.consumeToken();
                while (A.type === 31);
                if (A.type === 32) return t;
                throw new SyntaxError(
                    "Error parsing CSS component value, multiple values found when expecting only one"
                );
            }),
            (e.prototype.parseComponentValues = function () {
                for (var A = []; ; ) {
                    var t = this.consumeComponentValue();
                    if (t.type === 32) return A;
                    A.push(t), A.push();
                }
            }),
            (e.prototype.consumeComponentValue = function () {
                var A = this.consumeToken();
                switch (A.type) {
                    case 11:
                    case 28:
                    case 2:
                        return this.consumeSimpleBlock(A.type);
                    case 19:
                        return this.consumeFunction(A);
                }
                return A;
            }),
            (e.prototype.consumeSimpleBlock = function (A) {
                for (var t = { type: A, values: [] }, r = this.consumeToken(); ; ) {
                    if (r.type === 32 || Ri(r, A)) return t;
                    this.reconsumeToken(r), t.values.push(this.consumeComponentValue()), (r = this.consumeToken());
                }
            }),
            (e.prototype.consumeFunction = function (A) {
                for (var t = { name: A.value, values: [], type: 18 }; ; ) {
                    var r = this.consumeToken();
                    if (r.type === 32 || r.type === 3) return t;
                    this.reconsumeToken(r), t.values.push(this.consumeComponentValue());
                }
            }),
            (e.prototype.consumeToken = function () {
                var A = this._tokens.shift();
                return typeof A == "undefined" ? er : A;
            }),
            (e.prototype.reconsumeToken = function (A) {
                this._tokens.unshift(A);
            }),
            e
        );
    })(),
    de = function (e) {
        return e.type === 15;
    },
    zA = function (e) {
        return e.type === 17;
    },
    x = function (e) {
        return e.type === 20;
    },
    Mi = function (e) {
        return e.type === 0;
    },
    tr = function (e, A) {
        return x(e) && e.value === A;
    },
    Yn = function (e) {
        return e.type !== 31;
    },
    jA = function (e) {
        return e.type !== 31 && e.type !== 4;
    },
    oA = function (e) {
        var A = [],
            t = [];
        return (
            e.forEach(function (r) {
                if (r.type === 4) {
                    if (t.length === 0) throw new Error("Error parsing function args, zero tokens for arg");
                    A.push(t), (t = []);
                    return;
                }
                r.type !== 31 && t.push(r);
            }),
            t.length && A.push(t),
            A
        );
    },
    Ri = function (e, A) {
        return (A === 11 && e.type === 12) || (A === 28 && e.type === 29) ? !0 : A === 2 && e.type === 3;
    },
    yA = function (e) {
        return e.type === 17 || e.type === 15;
    },
    R = function (e) {
        return e.type === 16 || yA(e);
    },
    Wn = function (e) {
        return e.length > 1 ? [e[0], e[1]] : [e[0]];
    },
    P = { type: 17, number: 0, flags: Fe },
    fr = { type: 16, number: 50, flags: Fe },
    HA = { type: 16, number: 100, flags: Fe },
    oe = function (e, A, t) {
        var r = e[0],
            n = e[1];
        return [D(r, A), D(typeof n != "undefined" ? n : r, t)];
    },
    D = function (e, A) {
        if (e.type === 16) return (e.number / 100) * A;
        if (de(e))
            switch (e.unit) {
                case "rem":
                case "em":
                    return 16 * e.number;
                case "px":
                default:
                    return e.number;
            }
        return e.number;
    },
    Zn = "deg",
    qn = "grad",
    jn = "rad",
    zn = "turn",
    ut = {
        name: "angle",
        parse: function (e, A) {
            if (A.type === 15)
                switch (A.unit) {
                    case Zn:
                        return (Math.PI * A.number) / 180;
                    case qn:
                        return (Math.PI / 200) * A.number;
                    case jn:
                        return A.number;
                    case zn:
                        return Math.PI * 2 * A.number;
                }
            throw new Error("Unsupported angle type");
        },
    },
    $n = function (e) {
        return e.type === 15 && (e.unit === Zn || e.unit === qn || e.unit === jn || e.unit === zn);
    },
    As = function (e) {
        var A = e
            .filter(x)
            .map(function (t) {
                return t.value;
            })
            .join(" ");
        switch (A) {
            case "to bottom right":
            case "to right bottom":
            case "left top":
            case "top left":
                return [P, P];
            case "to top":
            case "bottom":
                return tA(0);
            case "to bottom left":
            case "to left bottom":
            case "right top":
            case "top right":
                return [P, HA];
            case "to right":
            case "left":
                return tA(90);
            case "to top left":
            case "to left top":
            case "right bottom":
            case "bottom right":
                return [HA, HA];
            case "to bottom":
            case "top":
                return tA(180);
            case "to top right":
            case "to right top":
            case "left bottom":
            case "bottom left":
                return [HA, P];
            case "to left":
            case "right":
                return tA(270);
        }
        return 0;
    },
    tA = function (e) {
        return (Math.PI * e) / 180;
    },
    IA = {
        name: "color",
        parse: function (e, A) {
            if (A.type === 18) {
                var t = Ni[A.name];
                if (typeof t == "undefined")
                    throw new Error('Attempting to parse an unsupported color function "' + A.name + '"');
                return t(e, A.values);
            }
            if (A.type === 5) {
                if (A.value.length === 3) {
                    var r = A.value.substring(0, 1),
                        n = A.value.substring(1, 2),
                        s = A.value.substring(2, 3);
                    return vA(parseInt(r + r, 16), parseInt(n + n, 16), parseInt(s + s, 16), 1);
                }
                if (A.value.length === 4) {
                    var r = A.value.substring(0, 1),
                        n = A.value.substring(1, 2),
                        s = A.value.substring(2, 3),
                        B = A.value.substring(3, 4);
                    return vA(parseInt(r + r, 16), parseInt(n + n, 16), parseInt(s + s, 16), parseInt(B + B, 16) / 255);
                }
                if (A.value.length === 6) {
                    var r = A.value.substring(0, 2),
                        n = A.value.substring(2, 4),
                        s = A.value.substring(4, 6);
                    return vA(parseInt(r, 16), parseInt(n, 16), parseInt(s, 16), 1);
                }
                if (A.value.length === 8) {
                    var r = A.value.substring(0, 2),
                        n = A.value.substring(2, 4),
                        s = A.value.substring(4, 6),
                        B = A.value.substring(6, 8);
                    return vA(parseInt(r, 16), parseInt(n, 16), parseInt(s, 16), parseInt(B, 16) / 255);
                }
            }
            if (A.type === 20) {
                var i = wA[A.value.toUpperCase()];
                if (typeof i != "undefined") return i;
            }
            return wA.TRANSPARENT;
        },
    },
    mA = function (e) {
        return (255 & e) === 0;
    },
    G = function (e) {
        var A = 255 & e,
            t = 255 & (e >> 8),
            r = 255 & (e >> 16),
            n = 255 & (e >> 24);
        return A < 255 ? "rgba(" + n + "," + r + "," + t + "," + A / 255 + ")" : "rgb(" + n + "," + r + "," + t + ")";
    },
    vA = function (e, A, t, r) {
        return ((e << 24) | (A << 16) | (t << 8) | (Math.round(r * 255) << 0)) >>> 0;
    },
    _r = function (e, A) {
        if (e.type === 17) return e.number;
        if (e.type === 16) {
            var t = A === 3 ? 1 : 255;
            return A === 3 ? (e.number / 100) * t : Math.round((e.number / 100) * t);
        }
        return 0;
    },
    Xr = function (e, A) {
        var t = A.filter(jA);
        if (t.length === 3) {
            var r = t.map(_r),
                n = r[0],
                s = r[1],
                B = r[2];
            return vA(n, s, B, 1);
        }
        if (t.length === 4) {
            var i = t.map(_r),
                n = i[0],
                s = i[1],
                B = i[2],
                a = i[3];
            return vA(n, s, B, a);
        }
        return 0;
    };
function Lt(e, A, t) {
    return (
        t < 0 && (t += 1),
        t >= 1 && (t -= 1),
        t < 1 / 6 ? (A - e) * t * 6 + e : t < 1 / 2 ? A : t < 2 / 3 ? (A - e) * 6 * (2 / 3 - t) + e : e
    );
}
var Jr = function (e, A) {
        var t = A.filter(jA),
            r = t[0],
            n = t[1],
            s = t[2],
            B = t[3],
            i = (r.type === 17 ? tA(r.number) : ut.parse(e, r)) / (Math.PI * 2),
            a = R(n) ? n.number / 100 : 0,
            o = R(s) ? s.number / 100 : 0,
            c = typeof B != "undefined" && R(B) ? D(B, 1) : 1;
        if (a === 0) return vA(o * 255, o * 255, o * 255, 1);
        var l = o <= 0.5 ? o * (a + 1) : o + a - o * a,
            g = o * 2 - l,
            w = Lt(g, l, i + 1 / 3),
            Q = Lt(g, l, i),
            f = Lt(g, l, i - 1 / 3);
        return vA(w * 255, Q * 255, f * 255, c);
    },
    Ni = { hsl: Jr, hsla: Jr, rgb: Xr, rgba: Xr },
    ue = function (e, A) {
        return IA.parse(e, Jn.create(A).parseComponentValue());
    },
    wA = {
        ALICEBLUE: 4042850303,
        ANTIQUEWHITE: 4209760255,
        AQUA: 16777215,
        AQUAMARINE: 2147472639,
        AZURE: 4043309055,
        BEIGE: 4126530815,
        BISQUE: 4293182719,
        BLACK: 255,
        BLANCHEDALMOND: 4293643775,
        BLUE: 65535,
        BLUEVIOLET: 2318131967,
        BROWN: 2771004159,
        BURLYWOOD: 3736635391,
        CADETBLUE: 1604231423,
        CHARTREUSE: 2147418367,
        CHOCOLATE: 3530104575,
        CORAL: 4286533887,
        CORNFLOWERBLUE: 1687547391,
        CORNSILK: 4294499583,
        CRIMSON: 3692313855,
        CYAN: 16777215,
        DARKBLUE: 35839,
        DARKCYAN: 9145343,
        DARKGOLDENROD: 3095837695,
        DARKGRAY: 2846468607,
        DARKGREEN: 6553855,
        DARKGREY: 2846468607,
        DARKKHAKI: 3182914559,
        DARKMAGENTA: 2332068863,
        DARKOLIVEGREEN: 1433087999,
        DARKORANGE: 4287365375,
        DARKORCHID: 2570243327,
        DARKRED: 2332033279,
        DARKSALMON: 3918953215,
        DARKSEAGREEN: 2411499519,
        DARKSLATEBLUE: 1211993087,
        DARKSLATEGRAY: 793726975,
        DARKSLATEGREY: 793726975,
        DARKTURQUOISE: 13554175,
        DARKVIOLET: 2483082239,
        DEEPPINK: 4279538687,
        DEEPSKYBLUE: 12582911,
        DIMGRAY: 1768516095,
        DIMGREY: 1768516095,
        DODGERBLUE: 512819199,
        FIREBRICK: 2988581631,
        FLORALWHITE: 4294635775,
        FORESTGREEN: 579543807,
        FUCHSIA: 4278255615,
        GAINSBORO: 3705462015,
        GHOSTWHITE: 4177068031,
        GOLD: 4292280575,
        GOLDENROD: 3668254975,
        GRAY: 2155905279,
        GREEN: 8388863,
        GREENYELLOW: 2919182335,
        GREY: 2155905279,
        HONEYDEW: 4043305215,
        HOTPINK: 4285117695,
        INDIANRED: 3445382399,
        INDIGO: 1258324735,
        IVORY: 4294963455,
        KHAKI: 4041641215,
        LAVENDER: 3873897215,
        LAVENDERBLUSH: 4293981695,
        LAWNGREEN: 2096890111,
        LEMONCHIFFON: 4294626815,
        LIGHTBLUE: 2916673279,
        LIGHTCORAL: 4034953471,
        LIGHTCYAN: 3774873599,
        LIGHTGOLDENRODYELLOW: 4210742015,
        LIGHTGRAY: 3553874943,
        LIGHTGREEN: 2431553791,
        LIGHTGREY: 3553874943,
        LIGHTPINK: 4290167295,
        LIGHTSALMON: 4288707327,
        LIGHTSEAGREEN: 548580095,
        LIGHTSKYBLUE: 2278488831,
        LIGHTSLATEGRAY: 2005441023,
        LIGHTSLATEGREY: 2005441023,
        LIGHTSTEELBLUE: 2965692159,
        LIGHTYELLOW: 4294959359,
        LIME: 16711935,
        LIMEGREEN: 852308735,
        LINEN: 4210091775,
        MAGENTA: 4278255615,
        MAROON: 2147483903,
        MEDIUMAQUAMARINE: 1724754687,
        MEDIUMBLUE: 52735,
        MEDIUMORCHID: 3126187007,
        MEDIUMPURPLE: 2473647103,
        MEDIUMSEAGREEN: 1018393087,
        MEDIUMSLATEBLUE: 2070474495,
        MEDIUMSPRINGGREEN: 16423679,
        MEDIUMTURQUOISE: 1221709055,
        MEDIUMVIOLETRED: 3340076543,
        MIDNIGHTBLUE: 421097727,
        MINTCREAM: 4127193855,
        MISTYROSE: 4293190143,
        MOCCASIN: 4293178879,
        NAVAJOWHITE: 4292783615,
        NAVY: 33023,
        OLDLACE: 4260751103,
        OLIVE: 2155872511,
        OLIVEDRAB: 1804477439,
        ORANGE: 4289003775,
        ORANGERED: 4282712319,
        ORCHID: 3664828159,
        PALEGOLDENROD: 4008225535,
        PALEGREEN: 2566625535,
        PALETURQUOISE: 2951671551,
        PALEVIOLETRED: 3681588223,
        PAPAYAWHIP: 4293907967,
        PEACHPUFF: 4292524543,
        PERU: 3448061951,
        PINK: 4290825215,
        PLUM: 3718307327,
        POWDERBLUE: 2967529215,
        PURPLE: 2147516671,
        REBECCAPURPLE: 1714657791,
        RED: 4278190335,
        ROSYBROWN: 3163525119,
        ROYALBLUE: 1097458175,
        SADDLEBROWN: 2336560127,
        SALMON: 4202722047,
        SANDYBROWN: 4104413439,
        SEAGREEN: 780883967,
        SEASHELL: 4294307583,
        SIENNA: 2689740287,
        SILVER: 3233857791,
        SKYBLUE: 2278484991,
        SLATEBLUE: 1784335871,
        SLATEGRAY: 1887473919,
        SLATEGREY: 1887473919,
        SNOW: 4294638335,
        SPRINGGREEN: 16744447,
        STEELBLUE: 1182971135,
        TAN: 3535047935,
        TEAL: 8421631,
        THISTLE: 3636451583,
        TOMATO: 4284696575,
        TRANSPARENT: 0,
        TURQUOISE: 1088475391,
        VIOLET: 4001558271,
        WHEAT: 4125012991,
        WHITE: 4294967295,
        WHITESMOKE: 4126537215,
        YELLOW: 4294902015,
        YELLOWGREEN: 2597139199,
    },
    Gi = {
        name: "background-clip",
        initialValue: "border-box",
        prefix: !1,
        type: 1,
        parse: function (e, A) {
            return A.map(function (t) {
                if (x(t))
                    switch (t.value) {
                        case "padding-box":
                            return 1;
                        case "content-box":
                            return 2;
                    }
                return 0;
            });
        },
    },
    Vi = { name: "background-color", initialValue: "transparent", prefix: !1, type: 3, format: "color" },
    Qt = function (e, A) {
        var t = IA.parse(e, A[0]),
            r = A[1];
        return r && R(r) ? { color: t, stop: r } : { color: t, stop: null };
    },
    Yr = function (e, A) {
        var t = e[0],
            r = e[e.length - 1];
        t.stop === null && (t.stop = P), r.stop === null && (r.stop = HA);
        for (var n = [], s = 0, B = 0; B < e.length; B++) {
            var i = e[B].stop;
            if (i !== null) {
                var a = D(i, A);
                a > s ? n.push(a) : n.push(s), (s = a);
            } else n.push(null);
        }
        for (var o = null, B = 0; B < n.length; B++) {
            var c = n[B];
            if (c === null) o === null && (o = B);
            else if (o !== null) {
                for (var l = B - o, g = n[o - 1], w = (c - g) / (l + 1), Q = 1; Q <= l; Q++) n[o + Q - 1] = w * Q;
                o = null;
            }
        }
        return e.map(function (f, H) {
            var d = f.color;
            return { color: d, stop: Math.max(Math.min(1, n[H] / A), 0) };
        });
    },
    ki = function (e, A, t) {
        var r = A / 2,
            n = t / 2,
            s = D(e[0], A) - r,
            B = n - D(e[1], t);
        return (Math.atan2(B, s) + Math.PI * 2) % (Math.PI * 2);
    },
    Pi = function (e, A, t) {
        var r = typeof e == "number" ? e : ki(e, A, t),
            n = Math.abs(A * Math.sin(r)) + Math.abs(t * Math.cos(r)),
            s = A / 2,
            B = t / 2,
            i = n / 2,
            a = Math.sin(r - Math.PI / 2) * i,
            o = Math.cos(r - Math.PI / 2) * i;
        return [n, s - o, s + o, B - a, B + a];
    },
    nA = function (e, A) {
        return Math.sqrt(e * e + A * A);
    },
    Wr = function (e, A, t, r, n) {
        var s = [
            [0, 0],
            [0, A],
            [e, 0],
            [e, A],
        ];
        return s.reduce(
            function (B, i) {
                var a = i[0],
                    o = i[1],
                    c = nA(t - a, r - o);
                return (n ? c < B.optimumDistance : c > B.optimumDistance)
                    ? { optimumCorner: i, optimumDistance: c }
                    : B;
            },
            { optimumDistance: n ? 1 / 0 : -1 / 0, optimumCorner: null }
        ).optimumCorner;
    },
    _i = function (e, A, t, r, n) {
        var s = 0,
            B = 0;
        switch (e.size) {
            case 0:
                e.shape === 0
                    ? (s = B = Math.min(Math.abs(A), Math.abs(A - r), Math.abs(t), Math.abs(t - n)))
                    : e.shape === 1 &&
                      ((s = Math.min(Math.abs(A), Math.abs(A - r))), (B = Math.min(Math.abs(t), Math.abs(t - n))));
                break;
            case 2:
                if (e.shape === 0) s = B = Math.min(nA(A, t), nA(A, t - n), nA(A - r, t), nA(A - r, t - n));
                else if (e.shape === 1) {
                    var i = Math.min(Math.abs(t), Math.abs(t - n)) / Math.min(Math.abs(A), Math.abs(A - r)),
                        a = Wr(r, n, A, t, !0),
                        o = a[0],
                        c = a[1];
                    (s = nA(o - A, (c - t) / i)), (B = i * s);
                }
                break;
            case 1:
                e.shape === 0
                    ? (s = B = Math.max(Math.abs(A), Math.abs(A - r), Math.abs(t), Math.abs(t - n)))
                    : e.shape === 1 &&
                      ((s = Math.max(Math.abs(A), Math.abs(A - r))), (B = Math.max(Math.abs(t), Math.abs(t - n))));
                break;
            case 3:
                if (e.shape === 0) s = B = Math.max(nA(A, t), nA(A, t - n), nA(A - r, t), nA(A - r, t - n));
                else if (e.shape === 1) {
                    var i = Math.max(Math.abs(t), Math.abs(t - n)) / Math.max(Math.abs(A), Math.abs(A - r)),
                        l = Wr(r, n, A, t, !1),
                        o = l[0],
                        c = l[1];
                    (s = nA(o - A, (c - t) / i)), (B = i * s);
                }
                break;
        }
        return (
            Array.isArray(e.size) && ((s = D(e.size[0], r)), (B = e.size.length === 2 ? D(e.size[1], n) : s)), [s, B]
        );
    },
    Xi = function (e, A) {
        var t = tA(180),
            r = [];
        return (
            oA(A).forEach(function (n, s) {
                if (s === 0) {
                    var B = n[0];
                    if (B.type === 20 && B.value === "to") {
                        t = As(n);
                        return;
                    } else if ($n(B)) {
                        t = ut.parse(e, B);
                        return;
                    }
                }
                var i = Qt(e, n);
                r.push(i);
            }),
            { angle: t, stops: r, type: 1 }
        );
    },
    Ge = function (e, A) {
        var t = tA(180),
            r = [];
        return (
            oA(A).forEach(function (n, s) {
                if (s === 0) {
                    var B = n[0];
                    if (B.type === 20 && ["top", "left", "right", "bottom"].indexOf(B.value) !== -1) {
                        t = As(n);
                        return;
                    } else if ($n(B)) {
                        t = (ut.parse(e, B) + tA(270)) % tA(360);
                        return;
                    }
                }
                var i = Qt(e, n);
                r.push(i);
            }),
            { angle: t, stops: r, type: 1 }
        );
    },
    Ji = function (e, A) {
        var t = tA(180),
            r = [],
            n = 1,
            s = 0,
            B = 3,
            i = [];
        return (
            oA(A).forEach(function (a, o) {
                var c = a[0];
                if (o === 0) {
                    if (x(c) && c.value === "linear") {
                        n = 1;
                        return;
                    } else if (x(c) && c.value === "radial") {
                        n = 2;
                        return;
                    }
                }
                if (c.type === 18) {
                    if (c.name === "from") {
                        var l = IA.parse(e, c.values[0]);
                        r.push({ stop: P, color: l });
                    } else if (c.name === "to") {
                        var l = IA.parse(e, c.values[0]);
                        r.push({ stop: HA, color: l });
                    } else if (c.name === "color-stop") {
                        var g = c.values.filter(jA);
                        if (g.length === 2) {
                            var l = IA.parse(e, g[1]),
                                w = g[0];
                            zA(w) && r.push({ stop: { type: 16, number: w.number * 100, flags: w.flags }, color: l });
                        }
                    }
                }
            }),
            n === 1
                ? { angle: (t + tA(180)) % tA(360), stops: r, type: n }
                : { size: B, shape: s, stops: r, position: i, type: n }
        );
    },
    es = "closest-side",
    ts = "farthest-side",
    rs = "closest-corner",
    ns = "farthest-corner",
    ss = "circle",
    Bs = "ellipse",
    is = "cover",
    as = "contain",
    Yi = function (e, A) {
        var t = 0,
            r = 3,
            n = [],
            s = [];
        return (
            oA(A).forEach(function (B, i) {
                var a = !0;
                if (i === 0) {
                    var o = !1;
                    a = B.reduce(function (l, g) {
                        if (o)
                            if (x(g))
                                switch (g.value) {
                                    case "center":
                                        return s.push(fr), l;
                                    case "top":
                                    case "left":
                                        return s.push(P), l;
                                    case "right":
                                    case "bottom":
                                        return s.push(HA), l;
                                }
                            else (R(g) || yA(g)) && s.push(g);
                        else if (x(g))
                            switch (g.value) {
                                case ss:
                                    return (t = 0), !1;
                                case Bs:
                                    return (t = 1), !1;
                                case "at":
                                    return (o = !0), !1;
                                case es:
                                    return (r = 0), !1;
                                case is:
                                case ts:
                                    return (r = 1), !1;
                                case as:
                                case rs:
                                    return (r = 2), !1;
                                case ns:
                                    return (r = 3), !1;
                            }
                        else if (yA(g) || R(g)) return Array.isArray(r) || (r = []), r.push(g), !1;
                        return l;
                    }, a);
                }
                if (a) {
                    var c = Qt(e, B);
                    n.push(c);
                }
            }),
            { size: r, shape: t, stops: n, position: s, type: 2 }
        );
    },
    Ve = function (e, A) {
        var t = 0,
            r = 3,
            n = [],
            s = [];
        return (
            oA(A).forEach(function (B, i) {
                var a = !0;
                if (
                    (i === 0
                        ? (a = B.reduce(function (c, l) {
                              if (x(l))
                                  switch (l.value) {
                                      case "center":
                                          return s.push(fr), !1;
                                      case "top":
                                      case "left":
                                          return s.push(P), !1;
                                      case "right":
                                      case "bottom":
                                          return s.push(HA), !1;
                                  }
                              else if (R(l) || yA(l)) return s.push(l), !1;
                              return c;
                          }, a))
                        : i === 1 &&
                          (a = B.reduce(function (c, l) {
                              if (x(l))
                                  switch (l.value) {
                                      case ss:
                                          return (t = 0), !1;
                                      case Bs:
                                          return (t = 1), !1;
                                      case as:
                                      case es:
                                          return (r = 0), !1;
                                      case ts:
                                          return (r = 1), !1;
                                      case rs:
                                          return (r = 2), !1;
                                      case is:
                                      case ns:
                                          return (r = 3), !1;
                                  }
                              else if (yA(l) || R(l)) return Array.isArray(r) || (r = []), r.push(l), !1;
                              return c;
                          }, a)),
                    a)
                ) {
                    var o = Qt(e, B);
                    n.push(o);
                }
            }),
            { size: r, shape: t, stops: n, position: s, type: 2 }
        );
    },
    Wi = function (e) {
        return e.type === 1;
    },
    Zi = function (e) {
        return e.type === 2;
    },
    Cr = {
        name: "image",
        parse: function (e, A) {
            if (A.type === 22) {
                var t = { url: A.value, type: 0 };
                return e.cache.addImage(A.value), t;
            }
            if (A.type === 18) {
                var r = os[A.name];
                if (typeof r == "undefined")
                    throw new Error('Attempting to parse an unsupported image function "' + A.name + '"');
                return r(e, A.values);
            }
            throw new Error("Unsupported image type " + A.type);
        },
    };
function qi(e) {
    return !(e.type === 20 && e.value === "none") && (e.type !== 18 || !!os[e.name]);
}
var os = {
        "linear-gradient": Xi,
        "-moz-linear-gradient": Ge,
        "-ms-linear-gradient": Ge,
        "-o-linear-gradient": Ge,
        "-webkit-linear-gradient": Ge,
        "radial-gradient": Yi,
        "-moz-radial-gradient": Ve,
        "-ms-radial-gradient": Ve,
        "-o-radial-gradient": Ve,
        "-webkit-radial-gradient": Ve,
        "-webkit-gradient": Ji,
    },
    ji = {
        name: "background-image",
        initialValue: "none",
        type: 1,
        prefix: !1,
        parse: function (e, A) {
            if (A.length === 0) return [];
            var t = A[0];
            return t.type === 20 && t.value === "none"
                ? []
                : A.filter(function (r) {
                      return jA(r) && qi(r);
                  }).map(function (r) {
                      return Cr.parse(e, r);
                  });
        },
    },
    zi = {
        name: "background-origin",
        initialValue: "border-box",
        prefix: !1,
        type: 1,
        parse: function (e, A) {
            return A.map(function (t) {
                if (x(t))
                    switch (t.value) {
                        case "padding-box":
                            return 1;
                        case "content-box":
                            return 2;
                    }
                return 0;
            });
        },
    },
    $i = {
        name: "background-position",
        initialValue: "0% 0%",
        type: 1,
        prefix: !1,
        parse: function (e, A) {
            return oA(A)
                .map(function (t) {
                    return t.filter(R);
                })
                .map(Wn);
        },
    },
    Aa = {
        name: "background-repeat",
        initialValue: "repeat",
        prefix: !1,
        type: 1,
        parse: function (e, A) {
            return oA(A)
                .map(function (t) {
                    return t
                        .filter(x)
                        .map(function (r) {
                            return r.value;
                        })
                        .join(" ");
                })
                .map(ea);
        },
    },
    ea = function (e) {
        switch (e) {
            case "no-repeat":
                return 1;
            case "repeat-x":
            case "repeat no-repeat":
                return 2;
            case "repeat-y":
            case "no-repeat repeat":
                return 3;
            case "repeat":
            default:
                return 0;
        }
    },
    qA;
(function (e) {
    (e.AUTO = "auto"), (e.CONTAIN = "contain"), (e.COVER = "cover");
})(qA || (qA = {}));
var ta = {
        name: "background-size",
        initialValue: "0",
        prefix: !1,
        type: 1,
        parse: function (e, A) {
            return oA(A).map(function (t) {
                return t.filter(ra);
            });
        },
    },
    ra = function (e) {
        return x(e) || R(e);
    },
    wt = function (e) {
        return { name: "border-" + e + "-color", initialValue: "transparent", prefix: !1, type: 3, format: "color" };
    },
    na = wt("top"),
    sa = wt("right"),
    Ba = wt("bottom"),
    ia = wt("left"),
    ft = function (e) {
        return {
            name: "border-radius-" + e,
            initialValue: "0 0",
            prefix: !1,
            type: 1,
            parse: function (A, t) {
                return Wn(t.filter(R));
            },
        };
    },
    aa = ft("top-left"),
    oa = ft("top-right"),
    ca = ft("bottom-right"),
    la = ft("bottom-left"),
    Ct = function (e) {
        return {
            name: "border-" + e + "-style",
            initialValue: "solid",
            prefix: !1,
            type: 2,
            parse: function (A, t) {
                switch (t) {
                    case "none":
                        return 0;
                    case "dashed":
                        return 2;
                    case "dotted":
                        return 3;
                    case "double":
                        return 4;
                }
                return 1;
            },
        };
    },
    ga = Ct("top"),
    ua = Ct("right"),
    Qa = Ct("bottom"),
    wa = Ct("left"),
    ht = function (e) {
        return {
            name: "border-" + e + "-width",
            initialValue: "0",
            type: 0,
            prefix: !1,
            parse: function (A, t) {
                return de(t) ? t.number : 0;
            },
        };
    },
    fa = ht("top"),
    Ca = ht("right"),
    ha = ht("bottom"),
    Ua = ht("left"),
    Fa = { name: "color", initialValue: "transparent", prefix: !1, type: 3, format: "color" },
    da = {
        name: "direction",
        initialValue: "ltr",
        prefix: !1,
        type: 2,
        parse: function (e, A) {
            switch (A) {
                case "rtl":
                    return 1;
                case "ltr":
                default:
                    return 0;
            }
        },
    },
    pa = {
        name: "display",
        initialValue: "inline-block",
        prefix: !1,
        type: 1,
        parse: function (e, A) {
            return A.filter(x).reduce(function (t, r) {
                return t | Ea(r.value);
            }, 0);
        },
    },
    Ea = function (e) {
        switch (e) {
            case "block":
            case "-webkit-box":
                return 2;
            case "inline":
                return 4;
            case "run-in":
                return 8;
            case "flow":
                return 16;
            case "flow-root":
                return 32;
            case "table":
                return 64;
            case "flex":
            case "-webkit-flex":
                return 128;
            case "grid":
            case "-ms-grid":
                return 256;
            case "ruby":
                return 512;
            case "subgrid":
                return 1024;
            case "list-item":
                return 2048;
            case "table-row-group":
                return 4096;
            case "table-header-group":
                return 8192;
            case "table-footer-group":
                return 16384;
            case "table-row":
                return 32768;
            case "table-cell":
                return 65536;
            case "table-column-group":
                return 131072;
            case "table-column":
                return 262144;
            case "table-caption":
                return 524288;
            case "ruby-base":
                return 1048576;
            case "ruby-text":
                return 2097152;
            case "ruby-base-container":
                return 4194304;
            case "ruby-text-container":
                return 8388608;
            case "contents":
                return 16777216;
            case "inline-block":
                return 33554432;
            case "inline-list-item":
                return 67108864;
            case "inline-table":
                return 134217728;
            case "inline-flex":
                return 268435456;
            case "inline-grid":
                return 536870912;
        }
        return 0;
    },
    Ha = {
        name: "float",
        initialValue: "none",
        prefix: !1,
        type: 2,
        parse: function (e, A) {
            switch (A) {
                case "left":
                    return 1;
                case "right":
                    return 2;
                case "inline-start":
                    return 3;
                case "inline-end":
                    return 4;
            }
            return 0;
        },
    },
    va = {
        name: "letter-spacing",
        initialValue: "0",
        prefix: !1,
        type: 0,
        parse: function (e, A) {
            return A.type === 20 && A.value === "normal" ? 0 : A.type === 17 || A.type === 15 ? A.number : 0;
        },
    },
    tt;
(function (e) {
    (e.NORMAL = "normal"), (e.STRICT = "strict");
})(tt || (tt = {}));
var Ia = {
        name: "line-break",
        initialValue: "normal",
        prefix: !1,
        type: 2,
        parse: function (e, A) {
            switch (A) {
                case "strict":
                    return tt.STRICT;
                case "normal":
                default:
                    return tt.NORMAL;
            }
        },
    },
    ma = { name: "line-height", initialValue: "normal", prefix: !1, type: 4 },
    Zr = function (e, A) {
        return x(e) && e.value === "normal" ? 1.2 * A : e.type === 17 ? A * e.number : R(e) ? D(e, A) : A;
    },
    ya = {
        name: "list-style-image",
        initialValue: "none",
        type: 0,
        prefix: !1,
        parse: function (e, A) {
            return A.type === 20 && A.value === "none" ? null : Cr.parse(e, A);
        },
    },
    La = {
        name: "list-style-position",
        initialValue: "outside",
        prefix: !1,
        type: 2,
        parse: function (e, A) {
            switch (A) {
                case "inside":
                    return 0;
                case "outside":
                default:
                    return 1;
            }
        },
    },
    rr = {
        name: "list-style-type",
        initialValue: "none",
        prefix: !1,
        type: 2,
        parse: function (e, A) {
            switch (A) {
                case "disc":
                    return 0;
                case "circle":
                    return 1;
                case "square":
                    return 2;
                case "decimal":
                    return 3;
                case "cjk-decimal":
                    return 4;
                case "decimal-leading-zero":
                    return 5;
                case "lower-roman":
                    return 6;
                case "upper-roman":
                    return 7;
                case "lower-greek":
                    return 8;
                case "lower-alpha":
                    return 9;
                case "upper-alpha":
                    return 10;
                case "arabic-indic":
                    return 11;
                case "armenian":
                    return 12;
                case "bengali":
                    return 13;
                case "cambodian":
                    return 14;
                case "cjk-earthly-branch":
                    return 15;
                case "cjk-heavenly-stem":
                    return 16;
                case "cjk-ideographic":
                    return 17;
                case "devanagari":
                    return 18;
                case "ethiopic-numeric":
                    return 19;
                case "georgian":
                    return 20;
                case "gujarati":
                    return 21;
                case "gurmukhi":
                    return 22;
                case "hebrew":
                    return 22;
                case "hiragana":
                    return 23;
                case "hiragana-iroha":
                    return 24;
                case "japanese-formal":
                    return 25;
                case "japanese-informal":
                    return 26;
                case "kannada":
                    return 27;
                case "katakana":
                    return 28;
                case "katakana-iroha":
                    return 29;
                case "khmer":
                    return 30;
                case "korean-hangul-formal":
                    return 31;
                case "korean-hanja-formal":
                    return 32;
                case "korean-hanja-informal":
                    return 33;
                case "lao":
                    return 34;
                case "lower-armenian":
                    return 35;
                case "malayalam":
                    return 36;
                case "mongolian":
                    return 37;
                case "myanmar":
                    return 38;
                case "oriya":
                    return 39;
                case "persian":
                    return 40;
                case "simp-chinese-formal":
                    return 41;
                case "simp-chinese-informal":
                    return 42;
                case "tamil":
                    return 43;
                case "telugu":
                    return 44;
                case "thai":
                    return 45;
                case "tibetan":
                    return 46;
                case "trad-chinese-formal":
                    return 47;
                case "trad-chinese-informal":
                    return 48;
                case "upper-armenian":
                    return 49;
                case "disclosure-open":
                    return 50;
                case "disclosure-closed":
                    return 51;
                case "none":
                default:
                    return -1;
            }
        },
    },
    Ut = function (e) {
        return { name: "margin-" + e, initialValue: "0", prefix: !1, type: 4 };
    },
    Ka = Ut("top"),
    ba = Ut("right"),
    xa = Ut("bottom"),
    Da = Ut("left"),
    Sa = {
        name: "overflow",
        initialValue: "visible",
        prefix: !1,
        type: 1,
        parse: function (e, A) {
            return A.filter(x).map(function (t) {
                switch (t.value) {
                    case "hidden":
                        return 1;
                    case "scroll":
                        return 2;
                    case "clip":
                        return 3;
                    case "auto":
                        return 4;
                    case "visible":
                    default:
                        return 0;
                }
            });
        },
    },
    Ta = {
        name: "overflow-wrap",
        initialValue: "normal",
        prefix: !1,
        type: 2,
        parse: function (e, A) {
            switch (A) {
                case "break-word":
                    return "break-word";
                case "normal":
                default:
                    return "normal";
            }
        },
    },
    Ft = function (e) {
        return { name: "padding-" + e, initialValue: "0", prefix: !1, type: 3, format: "length-percentage" };
    },
    Oa = Ft("top"),
    Ma = Ft("right"),
    Ra = Ft("bottom"),
    Na = Ft("left"),
    Ga = {
        name: "text-align",
        initialValue: "left",
        prefix: !1,
        type: 2,
        parse: function (e, A) {
            switch (A) {
                case "right":
                    return 2;
                case "center":
                case "justify":
                    return 1;
                case "left":
                default:
                    return 0;
            }
        },
    },
    Va = {
        name: "position",
        initialValue: "static",
        prefix: !1,
        type: 2,
        parse: function (e, A) {
            switch (A) {
                case "relative":
                    return 1;
                case "absolute":
                    return 2;
                case "fixed":
                    return 3;
                case "sticky":
                    return 4;
            }
            return 0;
        },
    },
    ka = {
        name: "text-shadow",
        initialValue: "none",
        type: 1,
        prefix: !1,
        parse: function (e, A) {
            return A.length === 1 && tr(A[0], "none")
                ? []
                : oA(A).map(function (t) {
                      for (
                          var r = { color: wA.TRANSPARENT, offsetX: P, offsetY: P, blur: P }, n = 0, s = 0;
                          s < t.length;
                          s++
                      ) {
                          var B = t[s];
                          yA(B)
                              ? (n === 0 ? (r.offsetX = B) : n === 1 ? (r.offsetY = B) : (r.blur = B), n++)
                              : (r.color = IA.parse(e, B));
                      }
                      return r;
                  });
        },
    },
    Pa = {
        name: "text-transform",
        initialValue: "none",
        prefix: !1,
        type: 2,
        parse: function (e, A) {
            switch (A) {
                case "uppercase":
                    return 2;
                case "lowercase":
                    return 1;
                case "capitalize":
                    return 3;
            }
            return 0;
        },
    },
    _a = {
        name: "transform",
        initialValue: "none",
        prefix: !0,
        type: 0,
        parse: function (e, A) {
            if (A.type === 20 && A.value === "none") return null;
            if (A.type === 18) {
                var t = Ya[A.name];
                if (typeof t == "undefined")
                    throw new Error('Attempting to parse an unsupported transform function "' + A.name + '"');
                return t(A.values);
            }
            return null;
        },
    },
    Xa = function (e) {
        var A = e
            .filter(function (t) {
                return t.type === 17;
            })
            .map(function (t) {
                return t.number;
            });
        return A.length === 6 ? A : null;
    },
    Ja = function (e) {
        var A = e
                .filter(function (a) {
                    return a.type === 17;
                })
                .map(function (a) {
                    return a.number;
                }),
            t = A[0],
            r = A[1];
        A[2], A[3];
        var n = A[4],
            s = A[5];
        A[6], A[7], A[8], A[9], A[10], A[11];
        var B = A[12],
            i = A[13];
        return A[14], A[15], A.length === 16 ? [t, r, n, s, B, i] : null;
    },
    Ya = { matrix: Xa, matrix3d: Ja },
    qr = { type: 16, number: 50, flags: Fe },
    Wa = [qr, qr],
    Za = {
        name: "transform-origin",
        initialValue: "50% 50%",
        prefix: !0,
        type: 1,
        parse: function (e, A) {
            var t = A.filter(R);
            return t.length !== 2 ? Wa : [t[0], t[1]];
        },
    },
    qa = {
        name: "visible",
        initialValue: "none",
        prefix: !1,
        type: 2,
        parse: function (e, A) {
            switch (A) {
                case "hidden":
                    return 1;
                case "collapse":
                    return 2;
                case "visible":
                default:
                    return 0;
            }
        },
    },
    Qe;
(function (e) {
    (e.NORMAL = "normal"), (e.BREAK_ALL = "break-all"), (e.KEEP_ALL = "keep-all");
})(Qe || (Qe = {}));
var ja = {
        name: "word-break",
        initialValue: "normal",
        prefix: !1,
        type: 2,
        parse: function (e, A) {
            switch (A) {
                case "break-all":
                    return Qe.BREAK_ALL;
                case "keep-all":
                    return Qe.KEEP_ALL;
                case "normal":
                default:
                    return Qe.NORMAL;
            }
        },
    },
    za = {
        name: "z-index",
        initialValue: "auto",
        prefix: !1,
        type: 0,
        parse: function (e, A) {
            if (A.type === 20) return { auto: !0, order: 0 };
            if (zA(A)) return { auto: !1, order: A.number };
            throw new Error("Invalid z-index number parsed");
        },
    },
    cs = {
        name: "time",
        parse: function (e, A) {
            if (A.type === 15)
                switch (A.unit.toLowerCase()) {
                    case "s":
                        return 1e3 * A.number;
                    case "ms":
                        return A.number;
                }
            throw new Error("Unsupported time type");
        },
    },
    $a = {
        name: "opacity",
        initialValue: "1",
        type: 0,
        prefix: !1,
        parse: function (e, A) {
            return zA(A) ? A.number : 1;
        },
    },
    Ao = { name: "text-decoration-color", initialValue: "transparent", prefix: !1, type: 3, format: "color" },
    eo = {
        name: "text-decoration-line",
        initialValue: "none",
        prefix: !1,
        type: 1,
        parse: function (e, A) {
            return A.filter(x)
                .map(function (t) {
                    switch (t.value) {
                        case "underline":
                            return 1;
                        case "overline":
                            return 2;
                        case "line-through":
                            return 3;
                        case "none":
                            return 4;
                    }
                    return 0;
                })
                .filter(function (t) {
                    return t !== 0;
                });
        },
    },
    to = {
        name: "font-family",
        initialValue: "",
        prefix: !1,
        type: 1,
        parse: function (e, A) {
            var t = [],
                r = [];
            return (
                A.forEach(function (n) {
                    switch (n.type) {
                        case 20:
                        case 0:
                            t.push(n.value);
                            break;
                        case 17:
                            t.push(n.number.toString());
                            break;
                        case 4:
                            r.push(t.join(" ")), (t.length = 0);
                            break;
                    }
                }),
                t.length && r.push(t.join(" ")),
                r.map(function (n) {
                    return n.indexOf(" ") === -1 ? n : "'" + n + "'";
                })
            );
        },
    },
    ro = { name: "font-size", initialValue: "0", prefix: !1, type: 3, format: "length" },
    no = {
        name: "font-weight",
        initialValue: "normal",
        type: 0,
        prefix: !1,
        parse: function (e, A) {
            if (zA(A)) return A.number;
            if (x(A))
                switch (A.value) {
                    case "bold":
                        return 700;
                    case "normal":
                    default:
                        return 400;
                }
            return 400;
        },
    },
    so = {
        name: "font-variant",
        initialValue: "none",
        type: 1,
        prefix: !1,
        parse: function (e, A) {
            return A.filter(x).map(function (t) {
                return t.value;
            });
        },
    },
    Bo = {
        name: "font-style",
        initialValue: "normal",
        prefix: !1,
        type: 2,
        parse: function (e, A) {
            switch (A) {
                case "oblique":
                    return "oblique";
                case "italic":
                    return "italic";
                case "normal":
                default:
                    return "normal";
            }
        },
    },
    N = function (e, A) {
        return (e & A) !== 0;
    },
    io = {
        name: "content",
        initialValue: "none",
        type: 1,
        prefix: !1,
        parse: function (e, A) {
            if (A.length === 0) return [];
            var t = A[0];
            return t.type === 20 && t.value === "none" ? [] : A;
        },
    },
    ao = {
        name: "counter-increment",
        initialValue: "none",
        prefix: !0,
        type: 1,
        parse: function (e, A) {
            if (A.length === 0) return null;
            var t = A[0];
            if (t.type === 20 && t.value === "none") return null;
            for (var r = [], n = A.filter(Yn), s = 0; s < n.length; s++) {
                var B = n[s],
                    i = n[s + 1];
                if (B.type === 20) {
                    var a = i && zA(i) ? i.number : 1;
                    r.push({ counter: B.value, increment: a });
                }
            }
            return r;
        },
    },
    oo = {
        name: "counter-reset",
        initialValue: "none",
        prefix: !0,
        type: 1,
        parse: function (e, A) {
            if (A.length === 0) return [];
            for (var t = [], r = A.filter(Yn), n = 0; n < r.length; n++) {
                var s = r[n],
                    B = r[n + 1];
                if (x(s) && s.value !== "none") {
                    var i = B && zA(B) ? B.number : 0;
                    t.push({ counter: s.value, reset: i });
                }
            }
            return t;
        },
    },
    co = {
        name: "duration",
        initialValue: "0s",
        prefix: !1,
        type: 1,
        parse: function (e, A) {
            return A.filter(de).map(function (t) {
                return cs.parse(e, t);
            });
        },
    },
    lo = {
        name: "quotes",
        initialValue: "none",
        prefix: !0,
        type: 1,
        parse: function (e, A) {
            if (A.length === 0) return null;
            var t = A[0];
            if (t.type === 20 && t.value === "none") return null;
            var r = [],
                n = A.filter(Mi);
            if (n.length % 2 !== 0) return null;
            for (var s = 0; s < n.length; s += 2) {
                var B = n[s].value,
                    i = n[s + 1].value;
                r.push({ open: B, close: i });
            }
            return r;
        },
    },
    jr = function (e, A, t) {
        if (!e) return "";
        var r = e[Math.min(A, e.length - 1)];
        return r ? (t ? r.open : r.close) : "";
    },
    go = {
        name: "box-shadow",
        initialValue: "none",
        type: 1,
        prefix: !1,
        parse: function (e, A) {
            return A.length === 1 && tr(A[0], "none")
                ? []
                : oA(A).map(function (t) {
                      for (
                          var r = { color: 255, offsetX: P, offsetY: P, blur: P, spread: P, inset: !1 }, n = 0, s = 0;
                          s < t.length;
                          s++
                      ) {
                          var B = t[s];
                          tr(B, "inset")
                              ? (r.inset = !0)
                              : yA(B)
                              ? (n === 0
                                    ? (r.offsetX = B)
                                    : n === 1
                                    ? (r.offsetY = B)
                                    : n === 2
                                    ? (r.blur = B)
                                    : (r.spread = B),
                                n++)
                              : (r.color = IA.parse(e, B));
                      }
                      return r;
                  });
        },
    },
    uo = {
        name: "paint-order",
        initialValue: "normal",
        prefix: !1,
        type: 1,
        parse: function (e, A) {
            var t = [0, 1, 2],
                r = [];
            return (
                A.filter(x).forEach(function (n) {
                    switch (n.value) {
                        case "stroke":
                            r.push(1);
                            break;
                        case "fill":
                            r.push(0);
                            break;
                        case "markers":
                            r.push(2);
                            break;
                    }
                }),
                t.forEach(function (n) {
                    r.indexOf(n) === -1 && r.push(n);
                }),
                r
            );
        },
    },
    Qo = { name: "-webkit-text-stroke-color", initialValue: "currentcolor", prefix: !1, type: 3, format: "color" },
    wo = {
        name: "-webkit-text-stroke-width",
        initialValue: "0",
        type: 0,
        prefix: !1,
        parse: function (e, A) {
            return de(A) ? A.number : 0;
        },
    },
    fo = (function () {
        function e(A, t) {
            var r, n;
            (this.animationDuration = U(A, co, t.animationDuration)),
                (this.backgroundClip = U(A, Gi, t.backgroundClip)),
                (this.backgroundColor = U(A, Vi, t.backgroundColor)),
                (this.backgroundImage = U(A, ji, t.backgroundImage)),
                (this.backgroundOrigin = U(A, zi, t.backgroundOrigin)),
                (this.backgroundPosition = U(A, $i, t.backgroundPosition)),
                (this.backgroundRepeat = U(A, Aa, t.backgroundRepeat)),
                (this.backgroundSize = U(A, ta, t.backgroundSize)),
                (this.borderTopColor = U(A, na, t.borderTopColor)),
                (this.borderRightColor = U(A, sa, t.borderRightColor)),
                (this.borderBottomColor = U(A, Ba, t.borderBottomColor)),
                (this.borderLeftColor = U(A, ia, t.borderLeftColor)),
                (this.borderTopLeftRadius = U(A, aa, t.borderTopLeftRadius)),
                (this.borderTopRightRadius = U(A, oa, t.borderTopRightRadius)),
                (this.borderBottomRightRadius = U(A, ca, t.borderBottomRightRadius)),
                (this.borderBottomLeftRadius = U(A, la, t.borderBottomLeftRadius)),
                (this.borderTopStyle = U(A, ga, t.borderTopStyle)),
                (this.borderRightStyle = U(A, ua, t.borderRightStyle)),
                (this.borderBottomStyle = U(A, Qa, t.borderBottomStyle)),
                (this.borderLeftStyle = U(A, wa, t.borderLeftStyle)),
                (this.borderTopWidth = U(A, fa, t.borderTopWidth)),
                (this.borderRightWidth = U(A, Ca, t.borderRightWidth)),
                (this.borderBottomWidth = U(A, ha, t.borderBottomWidth)),
                (this.borderLeftWidth = U(A, Ua, t.borderLeftWidth)),
                (this.boxShadow = U(A, go, t.boxShadow)),
                (this.color = U(A, Fa, t.color)),
                (this.direction = U(A, da, t.direction)),
                (this.display = U(A, pa, t.display)),
                (this.float = U(A, Ha, t.cssFloat)),
                (this.fontFamily = U(A, to, t.fontFamily)),
                (this.fontSize = U(A, ro, t.fontSize)),
                (this.fontStyle = U(A, Bo, t.fontStyle)),
                (this.fontVariant = U(A, so, t.fontVariant)),
                (this.fontWeight = U(A, no, t.fontWeight)),
                (this.letterSpacing = U(A, va, t.letterSpacing)),
                (this.lineBreak = U(A, Ia, t.lineBreak)),
                (this.lineHeight = U(A, ma, t.lineHeight)),
                (this.listStyleImage = U(A, ya, t.listStyleImage)),
                (this.listStylePosition = U(A, La, t.listStylePosition)),
                (this.listStyleType = U(A, rr, t.listStyleType)),
                (this.marginTop = U(A, Ka, t.marginTop)),
                (this.marginRight = U(A, ba, t.marginRight)),
                (this.marginBottom = U(A, xa, t.marginBottom)),
                (this.marginLeft = U(A, Da, t.marginLeft)),
                (this.opacity = U(A, $a, t.opacity));
            var s = U(A, Sa, t.overflow);
            (this.overflowX = s[0]),
                (this.overflowY = s[s.length > 1 ? 1 : 0]),
                (this.overflowWrap = U(A, Ta, t.overflowWrap)),
                (this.paddingTop = U(A, Oa, t.paddingTop)),
                (this.paddingRight = U(A, Ma, t.paddingRight)),
                (this.paddingBottom = U(A, Ra, t.paddingBottom)),
                (this.paddingLeft = U(A, Na, t.paddingLeft)),
                (this.paintOrder = U(A, uo, t.paintOrder)),
                (this.position = U(A, Va, t.position)),
                (this.textAlign = U(A, Ga, t.textAlign)),
                (this.textDecorationColor = U(
                    A,
                    Ao,
                    (r = t.textDecorationColor) !== null && r !== void 0 ? r : t.color
                )),
                (this.textDecorationLine = U(
                    A,
                    eo,
                    (n = t.textDecorationLine) !== null && n !== void 0 ? n : t.textDecoration
                )),
                (this.textShadow = U(A, ka, t.textShadow)),
                (this.textTransform = U(A, Pa, t.textTransform)),
                (this.transform = U(A, _a, t.transform)),
                (this.transformOrigin = U(A, Za, t.transformOrigin)),
                (this.visibility = U(A, qa, t.visibility)),
                (this.webkitTextStrokeColor = U(A, Qo, t.webkitTextStrokeColor)),
                (this.webkitTextStrokeWidth = U(A, wo, t.webkitTextStrokeWidth)),
                (this.wordBreak = U(A, ja, t.wordBreak)),
                (this.zIndex = U(A, za, t.zIndex));
        }
        return (
            (e.prototype.isVisible = function () {
                return this.display > 0 && this.opacity > 0 && this.visibility === 0;
            }),
            (e.prototype.isTransparent = function () {
                return mA(this.backgroundColor);
            }),
            (e.prototype.isTransformed = function () {
                return this.transform !== null;
            }),
            (e.prototype.isPositioned = function () {
                return this.position !== 0;
            }),
            (e.prototype.isPositionedWithZIndex = function () {
                return this.isPositioned() && !this.zIndex.auto;
            }),
            (e.prototype.isFloating = function () {
                return this.float !== 0;
            }),
            (e.prototype.isInlineLevel = function () {
                return (
                    N(this.display, 4) ||
                    N(this.display, 33554432) ||
                    N(this.display, 268435456) ||
                    N(this.display, 536870912) ||
                    N(this.display, 67108864) ||
                    N(this.display, 134217728)
                );
            }),
            e
        );
    })(),
    Co = (function () {
        function e(A, t) {
            (this.content = U(A, io, t.content)), (this.quotes = U(A, lo, t.quotes));
        }
        return e;
    })(),
    zr = (function () {
        function e(A, t) {
            (this.counterIncrement = U(A, ao, t.counterIncrement)), (this.counterReset = U(A, oo, t.counterReset));
        }
        return e;
    })(),
    U = function (e, A, t) {
        var r = new Xn(),
            n = t !== null && typeof t != "undefined" ? t.toString() : A.initialValue;
        r.write(n);
        var s = new Jn(r.read());
        switch (A.type) {
            case 2:
                var B = s.parseComponentValue();
                return A.parse(e, x(B) ? B.value : A.initialValue);
            case 0:
                return A.parse(e, s.parseComponentValue());
            case 1:
                return A.parse(e, s.parseComponentValues());
            case 4:
                return s.parseComponentValue();
            case 3:
                switch (A.format) {
                    case "angle":
                        return ut.parse(e, s.parseComponentValue());
                    case "color":
                        return IA.parse(e, s.parseComponentValue());
                    case "image":
                        return Cr.parse(e, s.parseComponentValue());
                    case "length":
                        var i = s.parseComponentValue();
                        return yA(i) ? i : P;
                    case "length-percentage":
                        var a = s.parseComponentValue();
                        return R(a) ? a : P;
                    case "time":
                        return cs.parse(e, s.parseComponentValue());
                }
                break;
        }
    },
    ho = "data-html2canvas-debug",
    Uo = function (e) {
        var A = e.getAttribute(ho);
        switch (A) {
            case "all":
                return 1;
            case "clone":
                return 2;
            case "parse":
                return 3;
            case "render":
                return 4;
            default:
                return 0;
        }
    },
    nr = function (e, A) {
        var t = Uo(e);
        return t === 1 || A === t;
    },
    cA = (function () {
        function e(A, t) {
            if (((this.context = A), (this.textNodes = []), (this.elements = []), (this.flags = 0), nr(t, 3))) debugger;
            (this.styles = new fo(A, window.getComputedStyle(t, null))),
                ir(t) &&
                    (this.styles.animationDuration.some(function (r) {
                        return r > 0;
                    }) && (t.style.animationDuration = "0s"),
                    this.styles.transform !== null && (t.style.transform = "none")),
                (this.bounds = lt(this.context, t)),
                nr(t, 4) && (this.flags |= 16);
        }
        return e;
    })(),
    Fo =
        "AAAAAAAAAAAAEA4AGBkAAFAaAAACAAAAAAAIABAAGAAwADgACAAQAAgAEAAIABAACAAQAAgAEAAIABAACAAQAAgAEAAIABAAQABIAEQATAAIABAACAAQAAgAEAAIABAAVABcAAgAEAAIABAACAAQAGAAaABwAHgAgACIAI4AlgAIABAAmwCjAKgAsAC2AL4AvQDFAMoA0gBPAVYBWgEIAAgACACMANoAYgFkAWwBdAF8AX0BhQGNAZUBlgGeAaMBlQGWAasBswF8AbsBwwF0AcsBYwHTAQgA2wG/AOMBdAF8AekB8QF0AfkB+wHiAHQBfAEIAAMC5gQIAAsCEgIIAAgAFgIeAggAIgIpAggAMQI5AkACygEIAAgASAJQAlgCYAIIAAgACAAKBQoFCgUTBRMFGQUrBSsFCAAIAAgACAAIAAgACAAIAAgACABdAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACABoAmgCrwGvAQgAbgJ2AggAHgEIAAgACADnAXsCCAAIAAgAgwIIAAgACAAIAAgACACKAggAkQKZAggAPADJAAgAoQKkAqwCsgK6AsICCADJAggA0AIIAAgACAAIANYC3gIIAAgACAAIAAgACABAAOYCCAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAkASoB+QIEAAgACAA8AEMCCABCBQgACABJBVAFCAAIAAgACAAIAAgACAAIAAgACABTBVoFCAAIAFoFCABfBWUFCAAIAAgACAAIAAgAbQUIAAgACAAIAAgACABzBXsFfQWFBYoFigWKBZEFigWKBYoFmAWfBaYFrgWxBbkFCAAIAAgACAAIAAgACAAIAAgACAAIAMEFCAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAMgFCADQBQgACAAIAAgACAAIAAgACAAIAAgACAAIAO4CCAAIAAgAiQAIAAgACABAAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAD0AggACAD8AggACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIANYFCAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAMDvwAIAAgAJAIIAAgACAAIAAgACAAIAAgACwMTAwgACAB9BOsEGwMjAwgAKwMyAwsFYgE3A/MEPwMIAEUDTQNRAwgAWQOsAGEDCAAIAAgACAAIAAgACABpAzQFNQU2BTcFOAU5BToFNAU1BTYFNwU4BTkFOgU0BTUFNgU3BTgFOQU6BTQFNQU2BTcFOAU5BToFNAU1BTYFNwU4BTkFOgU0BTUFNgU3BTgFOQU6BTQFNQU2BTcFOAU5BToFNAU1BTYFNwU4BTkFOgU0BTUFNgU3BTgFOQU6BTQFNQU2BTcFOAU5BToFNAU1BTYFNwU4BTkFOgU0BTUFNgU3BTgFOQU6BTQFNQU2BTcFOAU5BToFNAU1BTYFNwU4BTkFOgU0BTUFNgU3BTgFOQU6BTQFNQU2BTcFOAU5BToFNAU1BTYFNwU4BTkFOgU0BTUFNgU3BTgFOQU6BTQFNQU2BTcFOAU5BToFNAU1BTYFNwU4BTkFOgU0BTUFNgU3BTgFOQU6BTQFNQU2BTcFOAU5BToFNAU1BTYFNwU4BTkFOgU0BTUFNgU3BTgFOQU6BTQFNQU2BTcFOAU5BToFNAU1BTYFNwU4BTkFOgU0BTUFNgU3BTgFOQU6BTQFNQU2BTcFOAU5BToFNAU1BTYFNwU4BTkFOgU0BTUFNgU3BTgFOQU6BTQFNQU2BTcFOAU5BToFNAU1BTYFNwU4BTkFOgU0BTUFNgU3BTgFOQU6BTQFNQU2BTcFOAU5BToFNAU1BTYFNwU4BTkFOgU0BTUFNgU3BTgFOQU6BTQFNQU2BTcFOAU5BToFNAU1BTYFNwU4BTkFOgU0BTUFNgU3BTgFOQU6BTQFNQU2BTcFOAU5BToFNAU1BTYFNwU4BTkFOgU0BTUFNgU3BTgFOQU6BTQFNQU2BTcFOAU5BToFNAU1BTYFNwU4BTkFOgU0BTUFNgU3BTgFOQU6BTQFNQU2BTcFOAU5BToFNAU1BTYFNwU4BTkFOgU0BTUFNgU3BTgFOQU6BTQFNQU2BTcFOAU5BToFNAU1BTYFNwU4BTkFIQUoBSwFCAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACABtAwgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACABMAEwACAAIAAgACAAIABgACAAIAAgACAC/AAgACAAyAQgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACACAAIAAwAAgACAAIAAgACAAIAAgACAAIAAAARABIAAgACAAIABQASAAIAAgAIABwAEAAjgCIABsAqAC2AL0AigDQAtwC+IJIQqVAZUBWQqVAZUBlQGVAZUBlQGrC5UBlQGVAZUBlQGVAZUBlQGVAXsKlQGVAbAK6wsrDGUMpQzlDJUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAZUBlQGVAfAKAAuZA64AtwCJALoC6ADwAAgAuACgA/oEpgO6AqsD+AAIAAgAswMIAAgACAAIAIkAuwP5AfsBwwPLAwgACAAIAAgACADRA9kDCAAIAOED6QMIAAgACAAIAAgACADuA/YDCAAIAP4DyQAIAAgABgQIAAgAXQAOBAgACAAIAAgACAAIABMECAAIAAgACAAIAAgACAD8AAQBCAAIAAgAGgQiBCoECAExBAgAEAEIAAgACAAIAAgACAAIAAgACAAIAAgACAA4BAgACABABEYECAAIAAgATAQYAQgAVAQIAAgACAAIAAgACAAIAAgACAAIAFoECAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgAOQEIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAB+BAcACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAEABhgSMBAgACAAIAAgAlAQIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAwAEAAQABAADAAMAAwADAAQABAAEAAQABAAEAAQABHATAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgAdQMIAAgACAAIAAgACAAIAMkACAAIAAgAfQMIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACACFA4kDCAAIAAgACAAIAOcBCAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAIcDCAAIAAgACAAIAAgACAAIAAgACAAIAJEDCAAIAAgACADFAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACABgBAgAZgQIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgAbAQCBXIECAAIAHkECAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACABAAJwEQACjBKoEsgQIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAC6BMIECAAIAAgACAAIAAgACABmBAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgAxwQIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAGYECAAIAAgAzgQIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgAigWKBYoFigWKBYoFigWKBd0FXwUIAOIF6gXxBYoF3gT5BQAGCAaKBYoFigWKBYoFigWKBYoFigWKBYoFigXWBIoFigWKBYoFigWKBYoFigWKBYsFEAaKBYoFigWKBYoFigWKBRQGCACKBYoFigWKBQgACAAIANEECAAIABgGigUgBggAJgYIAC4GMwaKBYoF0wQ3Bj4GigWKBYoFigWKBYoFigWKBYoFigWKBYoFigUIAAgACAAIAAgACAAIAAgAigWKBYoFigWKBYoFigWKBYoFigWKBYoFigWKBYoFigWKBYoFigWKBYoFigWKBYoFigWKBYoFigWKBYoFigWLBf///////wQABAAEAAQABAAEAAQABAAEAAQAAwAEAAQAAgAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAAAAAAAAAAAAAAAAAAAAAAAAAOAAAAAAAAAAQADgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAFAAUABQAFAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAAAAUAAAAFAAUAAAAFAAUAAAAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAAEAAQABAAEAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAFAAUABQAFAAUABQAFAAUABQAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAFAAUABQAFAAUAAQAAAAUABQAFAAUABQAFAAAAAAAFAAUAAAAFAAUABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEAAAAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUABQAFAAUABQAFAAUABQAFAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUABQAFAAUABQAFAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAFAAAAAAAFAAUAAQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABwAFAAUABQAFAAAABwAHAAcAAAAHAAcABwAFAAEAAAAAAAAAAAAAAAAAAAAAAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHAAcABwAFAAUABQAFAAcABwAFAAUAAAAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHAAAAAQABAAAAAAAAAAAAAAAFAAUABQAFAAAABwAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAHAAcABwAHAAcAAAAHAAcAAAAAAAUABQAHAAUAAQAHAAEABwAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAFAAUABQAFAAUABwABAAUABQAFAAUAAAAAAAAAAAAAAAEAAQABAAEAAQABAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABwAFAAUAAAAAAAAAAAAAAAAABQAFAAUABQAFAAUAAQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAFAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQABQANAAQABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQABAAEAAQABAAEAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAAEAAQABAAEAAQABAAEAAQABAAEAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEAAQABAAEAAQABAAEAAQABAAAAAAAAAAAAAAAAAAAAAAABQAHAAUABQAFAAAAAAAAAAcABQAFAAUABQAFAAQABAAEAAQABAAEAAQABAAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAFAAUAAAAFAAUABQAFAAUAAAAFAAUABQAAAAUABQAFAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUABQAAAAAAAAAAAAUABQAFAAcAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAHAAUAAAAHAAcABwAFAAUABQAFAAUABQAFAAUABwAHAAcABwAFAAcABwAAAAUABQAFAAUABQAFAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABwAHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAAAAUABwAHAAUABQAFAAUAAAAAAAcABwAAAAAABwAHAAUAAAAAAAAAAAAAAAAAAAAAAAAABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAAAAAABQAFAAcAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAAABwAHAAcABQAFAAAAAAAAAAAABQAFAAAAAAAFAAUABQAAAAAAAAAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAAAAAAAAAFAAAAAAAAAAAAAAAAAAAAAAAAAAAABwAFAAUABQAFAAUAAAAFAAUABwAAAAcABwAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUABQAFAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUAAAAFAAUABwAFAAUABQAFAAAAAAAHAAcAAAAAAAcABwAFAAAAAAAAAAAAAAAAAAAABQAFAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAcABwAAAAAAAAAHAAcABwAAAAcABwAHAAUAAAAAAAAAAAAAAAAAAAAAAAAABQAAAAAAAAAAAAAAAAAAAAAABQAHAAcABwAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABwAHAAcABwAAAAUABQAFAAAABQAFAAUABQAAAAAAAAAAAAAAAAAAAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAAAAcABQAHAAcABQAHAAcAAAAFAAcABwAAAAcABwAFAAUAAAAAAAAAAAAAAAAAAAAFAAUAAAAAAAAAAAAAAAAAAAAAAAAABQAFAAcABwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAAAAUABwAAAAAAAAAAAAAAAAAAAAAAAAAAAAUAAAAAAAAAAAAFAAcABwAFAAUABQAAAAUAAAAHAAcABwAHAAcABwAHAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUAAAAHAAUABQAFAAUABQAFAAUAAAAAAAAAAAAAAAAAAAAAAAUABQAFAAUABQAFAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAAABwAFAAUABQAFAAUABQAFAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAFAAUABQAFAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAAAAUAAAAFAAAAAAAAAAAABwAHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABwAFAAUABQAFAAUAAAAFAAUAAAAAAAAAAAAAAAUABQAFAAUABQAFAAUABQAFAAUABQAAAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAFAAUABwAFAAUABQAFAAUABQAAAAUABQAHAAcABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHAAcABQAFAAAAAAAAAAAABQAFAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAAAAcABQAFAAAAAAAAAAAAAAAAAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAFAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAHAAUABQAFAAUABQAFAAUABwAHAAcABwAHAAcABwAHAAUABwAHAAUABQAFAAUABQAFAAUABQAFAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAFAAUABwAHAAcABwAFAAUABwAHAAcAAAAAAAAAAAAHAAcABQAHAAcABwAHAAcABwAFAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAFAAcABwAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcABQAHAAUABQAFAAUABQAFAAUAAAAFAAAABQAAAAAABQAFAAUABQAFAAUABQAFAAcABwAHAAcABwAHAAUABQAFAAUABQAFAAUABQAFAAUAAAAAAAUABQAFAAUABQAHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAFAAUABQAFAAUABwAFAAcABwAHAAcABwAFAAcABwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUABQAFAAUABQAFAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUABwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHAAUABQAFAAUABwAHAAUABQAHAAUABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAcABQAFAAcABwAHAAUABwAFAAUABQAHAAcAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABwAHAAcABwAHAAcABwAHAAUABQAFAAUABQAFAAUABQAHAAcABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAFAAUAAAAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAcABQAFAAUABQAFAAUABQAAAAAAAAAAAAUAAAAAAAAAAAAAAAAABQAAAAAABwAFAAUAAAAAAAAAAAAAAAAABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAAABQAFAAUABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAFAAUABQAFAAUADgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAFAAUAAAAFAAUABQAFAAUABQAFAAUABQAFAAAAAAAAAAAABQAAAAAAAAAFAAAAAAAAAAAABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABwAHAAUABQAHAAAAAAAAAAAABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcABwAHAAcABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUAAAAAAAAAAAAAAAAABQAFAAUABQAFAAUABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAFAAUABQAFAAUABQAFAAUABQAHAAcAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAcABwAFAAUABQAFAAcABwAFAAUABwAHAAAAAAAAAAAAAAAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAFAAUABQAFAAcABwAFAAUABwAHAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAAAAAAAAAAAAAAAAAAAAAAFAAcAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUAAAAFAAUABQAAAAAABQAFAAAAAAAAAAAAAAAFAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcABQAFAAcABwAAAAAAAAAAAAAABwAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcABwAFAAcABwAFAAcABwAAAAcABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAFAAUABQAAAAAAAAAAAAAAAAAFAAUABQAAAAUABQAAAAAAAAAAAAAABQAFAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUABQAAAAAAAAAAAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcABQAHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUABQAFAAUABwAFAAUABQAFAAUABQAFAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABwAHAAcABQAFAAUABQAFAAUABQAFAAUABwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHAAcABwAFAAUABQAHAAcABQAHAAUABQAAAAAAAAAAAAAAAAAFAAAABwAHAAcABQAFAAUABQAFAAUABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABwAHAAcABwAAAAAABwAHAAAAAAAHAAcABwAAAAAAAAAAAAAAAAAAAAAAAAAFAAAAAAAAAAAAAAAAAAAAAAAAAAAABwAHAAAAAAAFAAUABQAFAAUABQAFAAAAAAAAAAUABQAFAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHAAcABwAFAAUABQAFAAUABQAFAAUABwAHAAUABQAFAAcABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAHAAcABQAFAAUABQAFAAUABwAFAAcABwAFAAcABQAFAAcABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAHAAcABQAFAAUABQAAAAAABwAHAAcABwAFAAUABwAFAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcABwAHAAUABQAFAAUABQAFAAUABQAHAAcABQAHAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABwAFAAcABwAFAAUABQAFAAUABQAHAAUAAAAAAAAAAAAAAAAAAAAAAAcABwAFAAUABQAFAAcABQAFAAUABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHAAcABwAFAAUABQAFAAUABQAFAAUABQAHAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHAAcABwAFAAUABQAFAAAAAAAFAAUABwAHAAcABwAFAAAAAAAAAAcAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUABQAFAAUABQAFAAUABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUAAAAAAAAAAAAAAAAAAAAAAAAABQAFAAUABQAFAAUABwAHAAUABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcABQAFAAUABQAFAAUABQAAAAUABQAFAAUABQAFAAcABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUAAAAHAAUABQAFAAUABQAFAAUABwAFAAUABwAFAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAFAAUABQAFAAUAAAAAAAAABQAAAAUABQAAAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAHAAcABwAHAAcAAAAFAAUAAAAHAAcABQAHAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUABwAHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUABQAFAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUABQAFAAUABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAAAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAAAAAAAAAAAAAAAAAAABQAFAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcABwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAAAAUABQAFAAAAAAAFAAUABQAFAAUABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAFAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAFAAUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAAAAAAAAAAABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAAAAAAAAAAAAAAAAAAAAAAFAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUABQAFAAUABQAAAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAFAAUABQAFAAUABQAAAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAFAAUABQAAAAAABQAFAAUABQAFAAUABQAAAAUABQAAAAUABQAFAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAUABQAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQAFAAUABQAFAAUABQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAFAAUABQAFAAUADgAOAA4ADgAOAA4ADwAPAA8ADwAPAA8ADwAPAA8ADwAPAA8ADwAPAA8ADwAPAA8ADwAPAA8ADwAPAA8ADwAPAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcABwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABwAHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAcABwAHAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAAAAAAAAAkACQAJAAkACQAJAAkACQAJAAkACQAJAAkACQAJAAkACQAJAAkACQAJAAkACQAJAAkACQAJAAkACQAJAAkACQAKAAoACgAKAAoACgAKAAoACgAKAAoACgAKAAoACgAKAAoACgAKAAoACgAKAAoACgAMAAwADAAMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkACQAJAAkACQAJAAkACQAJAAkACQAJAAkACQAJAAkACQAJAAkAAAAAAAAAAAAKAAoACgAKAAoACgAKAAoACgAKAAoACgAKAAoACgAKAAoACgAKAAoACgAKAAoACgAKAAoACgAKAAoACgAKAAoACgAAAAAAAAAAAAsADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwACwAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAMAAwADAAAAAAADgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOAA4ADgAOAA4ADgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADgAOAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA4ADgAAAAAAAAAAAAAAAAAAAAAADgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADgAOAA4ADgAOAA4ADgAOAA4ADgAOAAAAAAAAAAAADgAOAA4AAAAAAAAAAAAAAAAAAAAOAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADgAOAAAAAAAAAAAAAAAAAAAAAAAAAAAADgAAAAAAAAAAAAAAAAAAAAAAAAAOAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADgAOAA4ADgAAAA4ADgAOAA4ADgAOAAAADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4AAAAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAAAAAAAAAAAAAAAAAAAAAAAAAAAADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4AAAAAAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAAAA4AAAAOAAAAAAAAAAAAAAAAAA4AAAAAAAAAAAAAAAAADgAAAAAAAAAAAAAAAAAAAAAAAAAAAA4ADgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADgAAAAAADgAAAAAAAAAAAA4AAAAOAAAAAAAAAAAADgAOAA4AAAAOAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOAA4ADgAOAA4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOAA4ADgAAAAAAAAAAAAAAAAAAAAAAAAAOAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOAA4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA4ADgAOAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADgAOAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADgAAAAAAAAAAAA4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOAAAADgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOAA4ADgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA4ADgAOAA4ADgAOAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA4ADgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADgAAAAAADgAOAA4ADgAOAA4ADgAOAA4ADgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAAAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAAAAAAAAAAAAAAAAAAAAAAAAAAAADgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA4AAAAAAA4ADgAOAA4ADgAOAA4ADgAOAAAADgAOAA4ADgAAAAAAAAAAAAAAAAAAAAAAAAAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4AAAAAAAAAAAAAAAAADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOAA4ADgAOAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADgAOAA4ADgAOAA4ADgAOAAAAAAAAAAAAAAAAAAAAAAAAAAAADgAOAA4ADgAOAA4AAAAAAAAAAAAAAAAAAAAAAA4ADgAOAA4ADgAOAA4ADgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4AAAAOAA4ADgAOAA4ADgAAAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4ADgAOAA4AAAAAAAAAAAA=",
    $r = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
    ce = typeof Uint8Array == "undefined" ? [] : new Uint8Array(256);
for (var ke = 0; ke < $r.length; ke++) ce[$r.charCodeAt(ke)] = ke;
var po = function (e) {
        var A = e.length * 0.75,
            t = e.length,
            r,
            n = 0,
            s,
            B,
            i,
            a;
        e[e.length - 1] === "=" && (A--, e[e.length - 2] === "=" && A--);
        var o =
                typeof ArrayBuffer != "undefined" &&
                typeof Uint8Array != "undefined" &&
                typeof Uint8Array.prototype.slice != "undefined"
                    ? new ArrayBuffer(A)
                    : new Array(A),
            c = Array.isArray(o) ? o : new Uint8Array(o);
        for (r = 0; r < t; r += 4)
            (s = ce[e.charCodeAt(r)]),
                (B = ce[e.charCodeAt(r + 1)]),
                (i = ce[e.charCodeAt(r + 2)]),
                (a = ce[e.charCodeAt(r + 3)]),
                (c[n++] = (s << 2) | (B >> 4)),
                (c[n++] = ((B & 15) << 4) | (i >> 2)),
                (c[n++] = ((i & 3) << 6) | (a & 63));
        return o;
    },
    Eo = function (e) {
        for (var A = e.length, t = [], r = 0; r < A; r += 2) t.push((e[r + 1] << 8) | e[r]);
        return t;
    },
    Ho = function (e) {
        for (var A = e.length, t = [], r = 0; r < A; r += 4)
            t.push((e[r + 3] << 24) | (e[r + 2] << 16) | (e[r + 1] << 8) | e[r]);
        return t;
    },
    NA = 5,
    hr = 6 + 5,
    Kt = 2,
    vo = hr - NA,
    ls = 65536 >> NA,
    Io = 1 << NA,
    bt = Io - 1,
    mo = 1024 >> NA,
    yo = ls + mo,
    Lo = yo,
    Ko = 32,
    bo = Lo + Ko,
    xo = 65536 >> hr,
    Do = 1 << vo,
    So = Do - 1,
    An = function (e, A, t) {
        return e.slice ? e.slice(A, t) : new Uint16Array(Array.prototype.slice.call(e, A, t));
    },
    To = function (e, A, t) {
        return e.slice ? e.slice(A, t) : new Uint32Array(Array.prototype.slice.call(e, A, t));
    },
    Oo = function (e, A) {
        var t = po(e),
            r = Array.isArray(t) ? Ho(t) : new Uint32Array(t),
            n = Array.isArray(t) ? Eo(t) : new Uint16Array(t),
            s = 24,
            B = An(n, s / 2, r[4] / 2),
            i = r[5] === 2 ? An(n, (s + r[4]) / 2) : To(r, Math.ceil((s + r[4]) / 4));
        return new Mo(r[0], r[1], r[2], r[3], B, i);
    },
    Mo = (function () {
        function e(A, t, r, n, s, B) {
            (this.initialValue = A),
                (this.errorValue = t),
                (this.highStart = r),
                (this.highValueIndex = n),
                (this.index = s),
                (this.data = B);
        }
        return (
            (e.prototype.get = function (A) {
                var t;
                if (A >= 0) {
                    if (A < 55296 || (A > 56319 && A <= 65535))
                        return (t = this.index[A >> NA]), (t = (t << Kt) + (A & bt)), this.data[t];
                    if (A <= 65535)
                        return (t = this.index[ls + ((A - 55296) >> NA)]), (t = (t << Kt) + (A & bt)), this.data[t];
                    if (A < this.highStart)
                        return (
                            (t = bo - xo + (A >> hr)),
                            (t = this.index[t]),
                            (t += (A >> NA) & So),
                            (t = this.index[t]),
                            (t = (t << Kt) + (A & bt)),
                            this.data[t]
                        );
                    if (A <= 1114111) return this.data[this.highValueIndex];
                }
                return this.errorValue;
            }),
            e
        );
    })(),
    en = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
    Ro = typeof Uint8Array == "undefined" ? [] : new Uint8Array(256);
for (var Pe = 0; Pe < en.length; Pe++) Ro[en.charCodeAt(Pe)] = Pe;
var No = 1,
    xt = 2,
    Dt = 3,
    tn = 4,
    rn = 5,
    Go = 7,
    nn = 8,
    St = 9,
    Tt = 10,
    sn = 11,
    Bn = 12,
    an = 13,
    on = 14,
    Ot = 15,
    Vo = function (e) {
        for (var A = [], t = 0, r = e.length; t < r; ) {
            var n = e.charCodeAt(t++);
            if (n >= 55296 && n <= 56319 && t < r) {
                var s = e.charCodeAt(t++);
                (s & 64512) === 56320 ? A.push(((n & 1023) << 10) + (s & 1023) + 65536) : (A.push(n), t--);
            } else A.push(n);
        }
        return A;
    },
    ko = function () {
        for (var e = [], A = 0; A < arguments.length; A++) e[A] = arguments[A];
        if (String.fromCodePoint) return String.fromCodePoint.apply(String, e);
        var t = e.length;
        if (!t) return "";
        for (var r = [], n = -1, s = ""; ++n < t; ) {
            var B = e[n];
            B <= 65535 ? r.push(B) : ((B -= 65536), r.push((B >> 10) + 55296, (B % 1024) + 56320)),
                (n + 1 === t || r.length > 16384) && ((s += String.fromCharCode.apply(String, r)), (r.length = 0));
        }
        return s;
    },
    Po = Oo(Fo),
    AA = "×",
    Mt = "÷",
    _o = function (e) {
        return Po.get(e);
    },
    Xo = function (e, A, t) {
        var r = t - 2,
            n = A[r],
            s = A[t - 1],
            B = A[t];
        if (s === xt && B === Dt) return AA;
        if (s === xt || s === Dt || s === tn || B === xt || B === Dt || B === tn) return Mt;
        if (
            (s === nn && [nn, St, sn, Bn].indexOf(B) !== -1) ||
            ((s === sn || s === St) && (B === St || B === Tt)) ||
            ((s === Bn || s === Tt) && B === Tt) ||
            B === an ||
            B === rn ||
            B === Go ||
            s === No
        )
            return AA;
        if (s === an && B === on) {
            for (; n === rn; ) n = A[--r];
            if (n === on) return AA;
        }
        if (s === Ot && B === Ot) {
            for (var i = 0; n === Ot; ) i++, (n = A[--r]);
            if (i % 2 === 0) return AA;
        }
        return Mt;
    },
    Jo = function (e) {
        var A = Vo(e),
            t = A.length,
            r = 0,
            n = 0,
            s = A.map(_o);
        return {
            next: function () {
                if (r >= t) return { done: !0, value: null };
                for (var B = AA; r < t && (B = Xo(A, s, ++r)) === AA; );
                if (B !== AA || r === t) {
                    var i = ko.apply(null, A.slice(n, r));
                    return (n = r), { value: i, done: !1 };
                }
                return { done: !0, value: null };
            },
        };
    },
    Yo = function (e) {
        for (var A = Jo(e), t = [], r; !(r = A.next()).done; ) r.value && t.push(r.value.slice());
        return t;
    },
    Wo = function (e) {
        var A = 123;
        if (e.createRange) {
            var t = e.createRange();
            if (t.getBoundingClientRect) {
                var r = e.createElement("boundtest");
                (r.style.height = A + "px"), (r.style.display = "block"), e.body.appendChild(r), t.selectNode(r);
                var n = t.getBoundingClientRect(),
                    s = Math.round(n.height);
                if ((e.body.removeChild(r), s === A)) return !0;
            }
        }
        return !1;
    },
    Zo = function (e) {
        var A = e.createElement("boundtest");
        (A.style.width = "50px"),
            (A.style.display = "block"),
            (A.style.fontSize = "12px"),
            (A.style.letterSpacing = "0px"),
            (A.style.wordSpacing = "0px"),
            e.body.appendChild(A);
        var t = e.createRange();
        A.innerHTML = typeof "".repeat == "function" ? "&#128104;".repeat(10) : "";
        var r = A.firstChild,
            n = gt(r.data).map(function (a) {
                return O(a);
            }),
            s = 0,
            B = {},
            i = n.every(function (a, o) {
                t.setStart(r, s), t.setEnd(r, s + a.length);
                var c = t.getBoundingClientRect();
                s += a.length;
                var l = c.x > B.x || c.y > B.y;
                return (B = c), o === 0 ? !0 : l;
            });
        return e.body.removeChild(A), i;
    },
    qo = function () {
        return typeof new Image().crossOrigin != "undefined";
    },
    jo = function () {
        return typeof new XMLHttpRequest().responseType == "string";
    },
    zo = function (e) {
        var A = new Image(),
            t = e.createElement("canvas"),
            r = t.getContext("2d");
        if (!r) return !1;
        A.src = "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg'></svg>";
        try {
            r.drawImage(A, 0, 0), t.toDataURL();
        } catch (n) {
            return !1;
        }
        return !0;
    },
    cn = function (e) {
        return e[0] === 0 && e[1] === 255 && e[2] === 0 && e[3] === 255;
    },
    $o = function (e) {
        var A = e.createElement("canvas"),
            t = 100;
        (A.width = t), (A.height = t);
        var r = A.getContext("2d");
        if (!r) return Promise.reject(!1);
        (r.fillStyle = "rgb(0, 255, 0)"), r.fillRect(0, 0, t, t);
        var n = new Image(),
            s = A.toDataURL();
        n.src = s;
        var B = sr(t, t, 0, 0, n);
        return (
            (r.fillStyle = "red"),
            r.fillRect(0, 0, t, t),
            ln(B)
                .then(function (i) {
                    r.drawImage(i, 0, 0);
                    var a = r.getImageData(0, 0, t, t).data;
                    (r.fillStyle = "red"), r.fillRect(0, 0, t, t);
                    var o = e.createElement("div");
                    return (
                        (o.style.backgroundImage = "url(" + s + ")"),
                        (o.style.height = t + "px"),
                        cn(a) ? ln(sr(t, t, 0, 0, o)) : Promise.reject(!1)
                    );
                })
                .then(function (i) {
                    return r.drawImage(i, 0, 0), cn(r.getImageData(0, 0, t, t).data);
                })
                .catch(function () {
                    return !1;
                })
        );
    },
    sr = function (e, A, t, r, n) {
        var s = "http://www.w3.org/2000/svg",
            B = document.createElementNS(s, "svg"),
            i = document.createElementNS(s, "foreignObject");
        return (
            B.setAttributeNS(null, "width", e.toString()),
            B.setAttributeNS(null, "height", A.toString()),
            i.setAttributeNS(null, "width", "100%"),
            i.setAttributeNS(null, "height", "100%"),
            i.setAttributeNS(null, "x", t.toString()),
            i.setAttributeNS(null, "y", r.toString()),
            i.setAttributeNS(null, "externalResourcesRequired", "true"),
            B.appendChild(i),
            i.appendChild(n),
            B
        );
    },
    ln = function (e) {
        return new Promise(function (A, t) {
            var r = new Image();
            (r.onload = function () {
                return A(r);
            }),
                (r.onerror = t),
                (r.src =
                    "data:image/svg+xml;charset=utf-8," + encodeURIComponent(new XMLSerializer().serializeToString(e)));
        });
    },
    k = {
        get SUPPORT_RANGE_BOUNDS() {
            var e = Wo(document);
            return Object.defineProperty(k, "SUPPORT_RANGE_BOUNDS", { value: e }), e;
        },
        get SUPPORT_WORD_BREAKING() {
            var e = k.SUPPORT_RANGE_BOUNDS && Zo(document);
            return Object.defineProperty(k, "SUPPORT_WORD_BREAKING", { value: e }), e;
        },
        get SUPPORT_SVG_DRAWING() {
            var e = zo(document);
            return Object.defineProperty(k, "SUPPORT_SVG_DRAWING", { value: e }), e;
        },
        get SUPPORT_FOREIGNOBJECT_DRAWING() {
            var e =
                typeof Array.from == "function" && typeof window.fetch == "function"
                    ? $o(document)
                    : Promise.resolve(!1);
            return Object.defineProperty(k, "SUPPORT_FOREIGNOBJECT_DRAWING", { value: e }), e;
        },
        get SUPPORT_CORS_IMAGES() {
            var e = qo();
            return Object.defineProperty(k, "SUPPORT_CORS_IMAGES", { value: e }), e;
        },
        get SUPPORT_RESPONSE_TYPE() {
            var e = jo();
            return Object.defineProperty(k, "SUPPORT_RESPONSE_TYPE", { value: e }), e;
        },
        get SUPPORT_CORS_XHR() {
            var e = "withCredentials" in new XMLHttpRequest();
            return Object.defineProperty(k, "SUPPORT_CORS_XHR", { value: e }), e;
        },
        get SUPPORT_NATIVE_TEXT_SEGMENTATION() {
            var e = !!(typeof Intl != "undefined" && Intl.Segmenter);
            return Object.defineProperty(k, "SUPPORT_NATIVE_TEXT_SEGMENTATION", { value: e }), e;
        },
    },
    we = (function () {
        function e(A, t) {
            (this.text = A), (this.bounds = t);
        }
        return e;
    })(),
    Ac = function (e, A, t, r) {
        var n = rc(A, t),
            s = [],
            B = 0;
        return (
            n.forEach(function (i) {
                if (t.textDecorationLine.length || i.trim().length > 0)
                    if (k.SUPPORT_RANGE_BOUNDS) {
                        var a = gn(r, B, i.length).getClientRects();
                        if (a.length > 1) {
                            var o = Ur(i),
                                c = 0;
                            o.forEach(function (g) {
                                s.push(new we(g, fA.fromDOMRectList(e, gn(r, c + B, g.length).getClientRects()))),
                                    (c += g.length);
                            });
                        } else s.push(new we(i, fA.fromDOMRectList(e, a)));
                    } else {
                        var l = r.splitText(i.length);
                        s.push(new we(i, ec(e, r))), (r = l);
                    }
                else k.SUPPORT_RANGE_BOUNDS || (r = r.splitText(i.length));
                B += i.length;
            }),
            s
        );
    },
    ec = function (e, A) {
        var t = A.ownerDocument;
        if (t) {
            var r = t.createElement("html2canvaswrapper");
            r.appendChild(A.cloneNode(!0));
            var n = A.parentNode;
            if (n) {
                n.replaceChild(r, A);
                var s = lt(e, r);
                return r.firstChild && n.replaceChild(r.firstChild, r), s;
            }
        }
        return fA.EMPTY;
    },
    gn = function (e, A, t) {
        var r = e.ownerDocument;
        if (!r) throw new Error("Node has no owner document");
        var n = r.createRange();
        return n.setStart(e, A), n.setEnd(e, A + t), n;
    },
    Ur = function (e) {
        if (k.SUPPORT_NATIVE_TEXT_SEGMENTATION) {
            var A = new Intl.Segmenter(void 0, { granularity: "grapheme" });
            return Array.from(A.segment(e)).map(function (t) {
                return t.segment;
            });
        }
        return Yo(e);
    },
    tc = function (e, A) {
        if (k.SUPPORT_NATIVE_TEXT_SEGMENTATION) {
            var t = new Intl.Segmenter(void 0, { granularity: "word" });
            return Array.from(t.segment(e)).map(function (r) {
                return r.segment;
            });
        }
        return sc(e, A);
    },
    rc = function (e, A) {
        return A.letterSpacing !== 0 ? Ur(e) : tc(e, A);
    },
    nc = [32, 160, 4961, 65792, 65793, 4153, 4241],
    sc = function (e, A) {
        for (
            var t = bB(e, {
                    lineBreak: A.lineBreak,
                    wordBreak: A.overflowWrap === "break-word" ? "break-word" : A.wordBreak,
                }),
                r = [],
                n,
                s = function () {
                    if (n.value) {
                        var B = n.value.slice(),
                            i = gt(B),
                            a = "";
                        i.forEach(function (o) {
                            nc.indexOf(o) === -1 ? (a += O(o)) : (a.length && r.push(a), r.push(O(o)), (a = ""));
                        }),
                            a.length && r.push(a);
                    }
                };
            !(n = t.next()).done;

        )
            s();
        return r;
    },
    Bc = (function () {
        function e(A, t, r) {
            (this.text = ic(t.data, r.textTransform)), (this.textBounds = Ac(A, this.text, r, t));
        }
        return e;
    })(),
    ic = function (e, A) {
        switch (A) {
            case 1:
                return e.toLowerCase();
            case 3:
                return e.replace(ac, oc);
            case 2:
                return e.toUpperCase();
            default:
                return e;
        }
    },
    ac = /(^|\s|:|-|\(|\))([a-z])/g,
    oc = function (e, A, t) {
        return e.length > 0 ? A + t.toUpperCase() : e;
    },
    gs = (function (e) {
        sA(A, e);
        function A(t, r) {
            var n = e.call(this, t, r) || this;
            return (
                (n.src = r.currentSrc || r.src),
                (n.intrinsicWidth = r.naturalWidth),
                (n.intrinsicHeight = r.naturalHeight),
                n.context.cache.addImage(n.src),
                n
            );
        }
        return A;
    })(cA),
    us = (function (e) {
        sA(A, e);
        function A(t, r) {
            var n = e.call(this, t, r) || this;
            return (n.canvas = r), (n.intrinsicWidth = r.width), (n.intrinsicHeight = r.height), n;
        }
        return A;
    })(cA),
    Qs = (function (e) {
        sA(A, e);
        function A(t, r) {
            var n = e.call(this, t, r) || this,
                s = new XMLSerializer(),
                B = lt(t, r);
            return (
                r.setAttribute("width", B.width + "px"),
                r.setAttribute("height", B.height + "px"),
                (n.svg = "data:image/svg+xml," + encodeURIComponent(s.serializeToString(r))),
                (n.intrinsicWidth = r.width.baseVal.value),
                (n.intrinsicHeight = r.height.baseVal.value),
                n.context.cache.addImage(n.svg),
                n
            );
        }
        return A;
    })(cA),
    ws = (function (e) {
        sA(A, e);
        function A(t, r) {
            var n = e.call(this, t, r) || this;
            return (n.value = r.value), n;
        }
        return A;
    })(cA),
    Br = (function (e) {
        sA(A, e);
        function A(t, r) {
            var n = e.call(this, t, r) || this;
            return (n.start = r.start), (n.reversed = typeof r.reversed == "boolean" && r.reversed === !0), n;
        }
        return A;
    })(cA),
    cc = [{ type: 15, flags: 0, unit: "px", number: 3 }],
    lc = [{ type: 16, flags: 0, number: 50 }],
    gc = function (e) {
        return e.width > e.height
            ? new fA(e.left + (e.width - e.height) / 2, e.top, e.height, e.height)
            : e.width < e.height
            ? new fA(e.left, e.top + (e.height - e.width) / 2, e.width, e.width)
            : e;
    },
    uc = function (e) {
        var A = e.type === Qc ? new Array(e.value.length + 1).join("•") : e.value;
        return A.length === 0 ? e.placeholder || "" : A;
    },
    rt = "checkbox",
    nt = "radio",
    Qc = "password",
    un = 707406591,
    Fr = (function (e) {
        sA(A, e);
        function A(t, r) {
            var n = e.call(this, t, r) || this;
            switch (
                ((n.type = r.type.toLowerCase()),
                (n.checked = r.checked),
                (n.value = uc(r)),
                (n.type === rt || n.type === nt) &&
                    ((n.styles.backgroundColor = 3739148031),
                    (n.styles.borderTopColor =
                        n.styles.borderRightColor =
                        n.styles.borderBottomColor =
                        n.styles.borderLeftColor =
                            2779096575),
                    (n.styles.borderTopWidth =
                        n.styles.borderRightWidth =
                        n.styles.borderBottomWidth =
                        n.styles.borderLeftWidth =
                            1),
                    (n.styles.borderTopStyle =
                        n.styles.borderRightStyle =
                        n.styles.borderBottomStyle =
                        n.styles.borderLeftStyle =
                            1),
                    (n.styles.backgroundClip = [0]),
                    (n.styles.backgroundOrigin = [0]),
                    (n.bounds = gc(n.bounds))),
                n.type)
            ) {
                case rt:
                    n.styles.borderTopRightRadius =
                        n.styles.borderTopLeftRadius =
                        n.styles.borderBottomRightRadius =
                        n.styles.borderBottomLeftRadius =
                            cc;
                    break;
                case nt:
                    n.styles.borderTopRightRadius =
                        n.styles.borderTopLeftRadius =
                        n.styles.borderBottomRightRadius =
                        n.styles.borderBottomLeftRadius =
                            lc;
                    break;
            }
            return n;
        }
        return A;
    })(cA),
    fs = (function (e) {
        sA(A, e);
        function A(t, r) {
            var n = e.call(this, t, r) || this,
                s = r.options[r.selectedIndex || 0];
            return (n.value = (s && s.text) || ""), n;
        }
        return A;
    })(cA),
    Cs = (function (e) {
        sA(A, e);
        function A(t, r) {
            var n = e.call(this, t, r) || this;
            return (n.value = r.value), n;
        }
        return A;
    })(cA),
    hs = (function (e) {
        sA(A, e);
        function A(t, r) {
            var n = e.call(this, t, r) || this;
            (n.src = r.src),
                (n.width = parseInt(r.width, 10) || 0),
                (n.height = parseInt(r.height, 10) || 0),
                (n.backgroundColor = n.styles.backgroundColor);
            try {
                if (r.contentWindow && r.contentWindow.document && r.contentWindow.document.documentElement) {
                    n.tree = Fs(t, r.contentWindow.document.documentElement);
                    var s = r.contentWindow.document.documentElement
                            ? ue(t, getComputedStyle(r.contentWindow.document.documentElement).backgroundColor)
                            : wA.TRANSPARENT,
                        B = r.contentWindow.document.body
                            ? ue(t, getComputedStyle(r.contentWindow.document.body).backgroundColor)
                            : wA.TRANSPARENT;
                    n.backgroundColor = mA(s) ? (mA(B) ? n.styles.backgroundColor : B) : s;
                }
            } catch (i) {}
            return n;
        }
        return A;
    })(cA),
    wc = ["OL", "UL", "MENU"],
    je = function (e, A, t, r) {
        for (var n = A.firstChild, s = void 0; n; n = s)
            if (((s = n.nextSibling), ds(n) && n.data.trim().length > 0)) t.textNodes.push(new Bc(e, n, t.styles));
            else if (ZA(n))
                if (vs(n) && n.assignedNodes)
                    n.assignedNodes().forEach(function (i) {
                        return je(e, i, t, r);
                    });
                else {
                    var B = Us(e, n);
                    B.styles.isVisible() &&
                        (fc(n, B, r) ? (B.flags |= 4) : Cc(B.styles) && (B.flags |= 2),
                        wc.indexOf(n.tagName) !== -1 && (B.flags |= 8),
                        t.elements.push(B),
                        n.slot,
                        n.shadowRoot ? je(e, n.shadowRoot, B, r) : !st(n) && !ps(n) && !Bt(n) && je(e, n, B, r));
                }
    },
    Us = function (e, A) {
        return ar(A)
            ? new gs(e, A)
            : Es(A)
            ? new us(e, A)
            : ps(A)
            ? new Qs(e, A)
            : hc(A)
            ? new ws(e, A)
            : Uc(A)
            ? new Br(e, A)
            : Fc(A)
            ? new Fr(e, A)
            : Bt(A)
            ? new fs(e, A)
            : st(A)
            ? new Cs(e, A)
            : Hs(A)
            ? new hs(e, A)
            : new cA(e, A);
    },
    Fs = function (e, A) {
        var t = Us(e, A);
        return (t.flags |= 4), je(e, A, t, t), t;
    },
    fc = function (e, A, t) {
        return (
            A.styles.isPositionedWithZIndex() ||
            A.styles.opacity < 1 ||
            A.styles.isTransformed() ||
            (dr(e) && t.styles.isTransparent())
        );
    },
    Cc = function (e) {
        return e.isPositioned() || e.isFloating();
    },
    ds = function (e) {
        return e.nodeType === Node.TEXT_NODE;
    },
    ZA = function (e) {
        return e.nodeType === Node.ELEMENT_NODE;
    },
    ir = function (e) {
        return ZA(e) && typeof e.style != "undefined" && !ze(e);
    },
    ze = function (e) {
        return typeof e.className == "object";
    },
    hc = function (e) {
        return e.tagName === "LI";
    },
    Uc = function (e) {
        return e.tagName === "OL";
    },
    Fc = function (e) {
        return e.tagName === "INPUT";
    },
    dc = function (e) {
        return e.tagName === "HTML";
    },
    ps = function (e) {
        return e.tagName === "svg";
    },
    dr = function (e) {
        return e.tagName === "BODY";
    },
    Es = function (e) {
        return e.tagName === "CANVAS";
    },
    Qn = function (e) {
        return e.tagName === "VIDEO";
    },
    ar = function (e) {
        return e.tagName === "IMG";
    },
    Hs = function (e) {
        return e.tagName === "IFRAME";
    },
    wn = function (e) {
        return e.tagName === "STYLE";
    },
    pc = function (e) {
        return e.tagName === "SCRIPT";
    },
    st = function (e) {
        return e.tagName === "TEXTAREA";
    },
    Bt = function (e) {
        return e.tagName === "SELECT";
    },
    vs = function (e) {
        return e.tagName === "SLOT";
    },
    fn = function (e) {
        return e.tagName.indexOf("-") > 0;
    },
    Ec = (function () {
        function e() {
            this.counters = {};
        }
        return (
            (e.prototype.getCounterValue = function (A) {
                var t = this.counters[A];
                return t && t.length ? t[t.length - 1] : 1;
            }),
            (e.prototype.getCounterValues = function (A) {
                var t = this.counters[A];
                return t || [];
            }),
            (e.prototype.pop = function (A) {
                var t = this;
                A.forEach(function (r) {
                    return t.counters[r].pop();
                });
            }),
            (e.prototype.parse = function (A) {
                var t = this,
                    r = A.counterIncrement,
                    n = A.counterReset,
                    s = !0;
                r !== null &&
                    r.forEach(function (i) {
                        var a = t.counters[i.counter];
                        a &&
                            i.increment !== 0 &&
                            ((s = !1), a.length || a.push(1), (a[Math.max(0, a.length - 1)] += i.increment));
                    });
                var B = [];
                return (
                    s &&
                        n.forEach(function (i) {
                            var a = t.counters[i.counter];
                            B.push(i.counter), a || (a = t.counters[i.counter] = []), a.push(i.reset);
                        }),
                    B
                );
            }),
            e
        );
    })(),
    Cn = {
        integers: [1e3, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1],
        values: ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"],
    },
    hn = {
        integers: [
            9e3, 8e3, 7e3, 6e3, 5e3, 4e3, 3e3, 2e3, 1e3, 900, 800, 700, 600, 500, 400, 300, 200, 100, 90, 80, 70, 60,
            50, 40, 30, 20, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1,
        ],
        values: [
            "Ք",
            "Փ",
            "Ւ",
            "Ց",
            "Ր",
            "Տ",
            "Վ",
            "Ս",
            "Ռ",
            "Ջ",
            "Պ",
            "Չ",
            "Ո",
            "Շ",
            "Ն",
            "Յ",
            "Մ",
            "Ճ",
            "Ղ",
            "Ձ",
            "Հ",
            "Կ",
            "Ծ",
            "Խ",
            "Լ",
            "Ի",
            "Ժ",
            "Թ",
            "Ը",
            "Է",
            "Զ",
            "Ե",
            "Դ",
            "Գ",
            "Բ",
            "Ա",
        ],
    },
    Hc = {
        integers: [
            1e4, 9e3, 8e3, 7e3, 6e3, 5e3, 4e3, 3e3, 2e3, 1e3, 400, 300, 200, 100, 90, 80, 70, 60, 50, 40, 30, 20, 19,
            18, 17, 16, 15, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1,
        ],
        values: [
            "י׳",
            "ט׳",
            "ח׳",
            "ז׳",
            "ו׳",
            "ה׳",
            "ד׳",
            "ג׳",
            "ב׳",
            "א׳",
            "ת",
            "ש",
            "ר",
            "ק",
            "צ",
            "פ",
            "ע",
            "ס",
            "נ",
            "מ",
            "ל",
            "כ",
            "יט",
            "יח",
            "יז",
            "טז",
            "טו",
            "י",
            "ט",
            "ח",
            "ז",
            "ו",
            "ה",
            "ד",
            "ג",
            "ב",
            "א",
        ],
    },
    vc = {
        integers: [
            1e4, 9e3, 8e3, 7e3, 6e3, 5e3, 4e3, 3e3, 2e3, 1e3, 900, 800, 700, 600, 500, 400, 300, 200, 100, 90, 80, 70,
            60, 50, 40, 30, 20, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1,
        ],
        values: [
            "ჵ",
            "ჰ",
            "ჯ",
            "ჴ",
            "ხ",
            "ჭ",
            "წ",
            "ძ",
            "ც",
            "ჩ",
            "შ",
            "ყ",
            "ღ",
            "ქ",
            "ფ",
            "ჳ",
            "ტ",
            "ს",
            "რ",
            "ჟ",
            "პ",
            "ო",
            "ჲ",
            "ნ",
            "მ",
            "ლ",
            "კ",
            "ი",
            "თ",
            "ჱ",
            "ზ",
            "ვ",
            "ე",
            "დ",
            "გ",
            "ბ",
            "ა",
        ],
    },
    _A = function (e, A, t, r, n, s) {
        return e < A || e > t
            ? Ue(e, n, s.length > 0)
            : r.integers.reduce(function (B, i, a) {
                  for (; e >= i; ) (e -= i), (B += r.values[a]);
                  return B;
              }, "") + s;
    },
    Is = function (e, A, t, r) {
        var n = "";
        do t || e--, (n = r(e) + n), (e /= A);
        while (e * A >= A);
        return n;
    },
    T = function (e, A, t, r, n) {
        var s = t - A + 1;
        return (
            (e < 0 ? "-" : "") +
            (Is(Math.abs(e), s, r, function (B) {
                return O(Math.floor(B % s) + A);
            }) +
                n)
        );
    },
    SA = function (e, A, t) {
        t === void 0 && (t = ". ");
        var r = A.length;
        return (
            Is(Math.abs(e), r, !1, function (n) {
                return A[Math.floor(n % r)];
            }) + t
        );
    },
    YA = 1 << 0,
    FA = 1 << 1,
    dA = 1 << 2,
    le = 1 << 3,
    QA = function (e, A, t, r, n, s) {
        if (e < -9999 || e > 9999) return Ue(e, 4, n.length > 0);
        var B = Math.abs(e),
            i = n;
        if (B === 0) return A[0] + i;
        for (var a = 0; B > 0 && a <= 4; a++) {
            var o = B % 10;
            o === 0 && N(s, YA) && i !== ""
                ? (i = A[o] + i)
                : o > 1 ||
                  (o === 1 && a === 0) ||
                  (o === 1 && a === 1 && N(s, FA)) ||
                  (o === 1 && a === 1 && N(s, dA) && e > 100) ||
                  (o === 1 && a > 1 && N(s, le))
                ? (i = A[o] + (a > 0 ? t[a - 1] : "") + i)
                : o === 1 && a > 0 && (i = t[a - 1] + i),
                (B = Math.floor(B / 10));
        }
        return (e < 0 ? r : "") + i;
    },
    Un = "十百千萬",
    Fn = "拾佰仟萬",
    dn = "マイナス",
    Rt = "마이너스",
    Ue = function (e, A, t) {
        var r = t ? ". " : "",
            n = t ? "、" : "",
            s = t ? ", " : "",
            B = t ? " " : "";
        switch (A) {
            case 0:
                return "•" + B;
            case 1:
                return "◦" + B;
            case 2:
                return "◾" + B;
            case 5:
                var i = T(e, 48, 57, !0, r);
                return i.length < 4 ? "0" + i : i;
            case 4:
                return SA(e, "〇一二三四五六七八九", n);
            case 6:
                return _A(e, 1, 3999, Cn, 3, r).toLowerCase();
            case 7:
                return _A(e, 1, 3999, Cn, 3, r);
            case 8:
                return T(e, 945, 969, !1, r);
            case 9:
                return T(e, 97, 122, !1, r);
            case 10:
                return T(e, 65, 90, !1, r);
            case 11:
                return T(e, 1632, 1641, !0, r);
            case 12:
            case 49:
                return _A(e, 1, 9999, hn, 3, r);
            case 35:
                return _A(e, 1, 9999, hn, 3, r).toLowerCase();
            case 13:
                return T(e, 2534, 2543, !0, r);
            case 14:
            case 30:
                return T(e, 6112, 6121, !0, r);
            case 15:
                return SA(e, "子丑寅卯辰巳午未申酉戌亥", n);
            case 16:
                return SA(e, "甲乙丙丁戊己庚辛壬癸", n);
            case 17:
            case 48:
                return QA(e, "零一二三四五六七八九", Un, "負", n, FA | dA | le);
            case 47:
                return QA(e, "零壹貳參肆伍陸柒捌玖", Fn, "負", n, YA | FA | dA | le);
            case 42:
                return QA(e, "零一二三四五六七八九", Un, "负", n, FA | dA | le);
            case 41:
                return QA(e, "零壹贰叁肆伍陆柒捌玖", Fn, "负", n, YA | FA | dA | le);
            case 26:
                return QA(e, "〇一二三四五六七八九", "十百千万", dn, n, 0);
            case 25:
                return QA(e, "零壱弐参四伍六七八九", "拾百千万", dn, n, YA | FA | dA);
            case 31:
                return QA(e, "영일이삼사오육칠팔구", "십백천만", Rt, s, YA | FA | dA);
            case 33:
                return QA(e, "零一二三四五六七八九", "十百千萬", Rt, s, 0);
            case 32:
                return QA(e, "零壹貳參四五六七八九", "拾百千", Rt, s, YA | FA | dA);
            case 18:
                return T(e, 2406, 2415, !0, r);
            case 20:
                return _A(e, 1, 19999, vc, 3, r);
            case 21:
                return T(e, 2790, 2799, !0, r);
            case 22:
                return T(e, 2662, 2671, !0, r);
            case 22:
                return _A(e, 1, 10999, Hc, 3, r);
            case 23:
                return SA(
                    e,
                    "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわゐゑをん"
                );
            case 24:
                return SA(
                    e,
                    "いろはにほへとちりぬるをわかよたれそつねならむうゐのおくやまけふこえてあさきゆめみしゑひもせす"
                );
            case 27:
                return T(e, 3302, 3311, !0, r);
            case 28:
                return SA(
                    e,
                    "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヰヱヲン",
                    n
                );
            case 29:
                return SA(
                    e,
                    "イロハニホヘトチリヌルヲワカヨタレソツネナラムウヰノオクヤマケフコエテアサキユメミシヱヒモセス",
                    n
                );
            case 34:
                return T(e, 3792, 3801, !0, r);
            case 37:
                return T(e, 6160, 6169, !0, r);
            case 38:
                return T(e, 4160, 4169, !0, r);
            case 39:
                return T(e, 2918, 2927, !0, r);
            case 40:
                return T(e, 1776, 1785, !0, r);
            case 43:
                return T(e, 3046, 3055, !0, r);
            case 44:
                return T(e, 3174, 3183, !0, r);
            case 45:
                return T(e, 3664, 3673, !0, r);
            case 46:
                return T(e, 3872, 3881, !0, r);
            case 3:
            default:
                return T(e, 48, 57, !0, r);
        }
    },
    ms = "data-html2canvas-ignore",
    pn = (function () {
        function e(A, t, r) {
            if (
                ((this.context = A),
                (this.options = r),
                (this.scrolledElements = []),
                (this.referenceElement = t),
                (this.counters = new Ec()),
                (this.quoteDepth = 0),
                !t.ownerDocument)
            )
                throw new Error("Cloned element does not have an owner document");
            this.documentElement = this.cloneNode(t.ownerDocument.documentElement, !1);
        }
        return (
            (e.prototype.toIFrame = function (A, t) {
                var r = this,
                    n = Ic(A, t);
                if (!n.contentWindow) return Promise.reject("Unable to find iframe window");
                var s = A.defaultView.pageXOffset,
                    B = A.defaultView.pageYOffset,
                    i = n.contentWindow,
                    a = i.document,
                    o = Lc(n).then(function () {
                        return J(r, void 0, void 0, function () {
                            var c, l;
                            return _(this, function (g) {
                                switch (g.label) {
                                    case 0:
                                        return (
                                            this.scrolledElements.forEach(Dc),
                                            i &&
                                                (i.scrollTo(t.left, t.top),
                                                /(iPad|iPhone|iPod)/g.test(navigator.userAgent) &&
                                                    (i.scrollY !== t.top || i.scrollX !== t.left) &&
                                                    (this.context.logger.warn(
                                                        "Unable to restore scroll position for cloned document"
                                                    ),
                                                    (this.context.windowBounds = this.context.windowBounds.add(
                                                        i.scrollX - t.left,
                                                        i.scrollY - t.top,
                                                        0,
                                                        0
                                                    )))),
                                            (c = this.options.onclone),
                                            (l = this.clonedReferenceElement),
                                            typeof l == "undefined"
                                                ? [
                                                      2,
                                                      Promise.reject(
                                                          "Error finding the " +
                                                              this.referenceElement.nodeName +
                                                              " in the cloned document"
                                                      ),
                                                  ]
                                                : a.fonts && a.fonts.ready
                                                ? [4, a.fonts.ready]
                                                : [3, 2]
                                        );
                                    case 1:
                                        g.sent(), (g.label = 2);
                                    case 2:
                                        return /(AppleWebKit)/g.test(navigator.userAgent) ? [4, yc(a)] : [3, 4];
                                    case 3:
                                        g.sent(), (g.label = 4);
                                    case 4:
                                        return typeof c == "function"
                                            ? [
                                                  2,
                                                  Promise.resolve()
                                                      .then(function () {
                                                          return c(a, l);
                                                      })
                                                      .then(function () {
                                                          return n;
                                                      }),
                                              ]
                                            : [2, n];
                                }
                            });
                        });
                    });
                return (
                    a.open(),
                    a.write(bc(document.doctype) + "<html></html>"),
                    xc(this.referenceElement.ownerDocument, s, B),
                    a.replaceChild(a.adoptNode(this.documentElement), a.documentElement),
                    a.close(),
                    o
                );
            }),
            (e.prototype.createElementClone = function (A) {
                if (nr(A, 2)) debugger;
                if (Es(A)) return this.createCanvasClone(A);
                if (Qn(A)) return this.createVideoClone(A);
                if (wn(A)) return this.createStyleClone(A);
                var t = A.cloneNode(!1);
                return (
                    ar(t) &&
                        (ar(A) && A.currentSrc && A.currentSrc !== A.src && ((t.src = A.currentSrc), (t.srcset = "")),
                        t.loading === "lazy" && (t.loading = "eager")),
                    fn(t) ? this.createCustomElementClone(t) : t
                );
            }),
            (e.prototype.createCustomElementClone = function (A) {
                var t = document.createElement("html2canvascustomelement");
                return Nt(A.style, t), t;
            }),
            (e.prototype.createStyleClone = function (A) {
                try {
                    var t = A.sheet;
                    if (t && t.cssRules) {
                        var r = [].slice.call(t.cssRules, 0).reduce(function (s, B) {
                                return B && typeof B.cssText == "string" ? s + B.cssText : s;
                            }, ""),
                            n = A.cloneNode(!1);
                        return (n.textContent = r), n;
                    }
                } catch (s) {
                    if (
                        (this.context.logger.error("Unable to access cssRules property", s), s.name !== "SecurityError")
                    )
                        throw s;
                }
                return A.cloneNode(!1);
            }),
            (e.prototype.createCanvasClone = function (A) {
                var t;
                if (this.options.inlineImages && A.ownerDocument) {
                    var r = A.ownerDocument.createElement("img");
                    try {
                        return (r.src = A.toDataURL()), r;
                    } catch (o) {
                        this.context.logger.info("Unable to inline canvas contents, canvas is tainted", A);
                    }
                }
                var n = A.cloneNode(!1);
                try {
                    (n.width = A.width), (n.height = A.height);
                    var s = A.getContext("2d"),
                        B = n.getContext("2d");
                    if (B)
                        if (!this.options.allowTaint && s)
                            B.putImageData(s.getImageData(0, 0, A.width, A.height), 0, 0);
                        else {
                            var i = (t = A.getContext("webgl2")) !== null && t !== void 0 ? t : A.getContext("webgl");
                            if (i) {
                                var a = i.getContextAttributes();
                                (a == null ? void 0 : a.preserveDrawingBuffer) === !1 &&
                                    this.context.logger.warn(
                                        "Unable to clone WebGL context as it has preserveDrawingBuffer=false",
                                        A
                                    );
                            }
                            B.drawImage(A, 0, 0);
                        }
                    return n;
                } catch (o) {
                    this.context.logger.info("Unable to clone canvas as it is tainted", A);
                }
                return n;
            }),
            (e.prototype.createVideoClone = function (A) {
                var t = A.ownerDocument.createElement("canvas");
                (t.width = A.offsetWidth), (t.height = A.offsetHeight);
                var r = t.getContext("2d");
                try {
                    return (
                        r &&
                            (r.drawImage(A, 0, 0, t.width, t.height),
                            this.options.allowTaint || r.getImageData(0, 0, t.width, t.height)),
                        t
                    );
                } catch (s) {
                    this.context.logger.info("Unable to clone video as it is tainted", A);
                }
                var n = A.ownerDocument.createElement("canvas");
                return (n.width = A.offsetWidth), (n.height = A.offsetHeight), n;
            }),
            (e.prototype.appendChildNode = function (A, t, r) {
                (!ZA(t) ||
                    (!pc(t) &&
                        !t.hasAttribute(ms) &&
                        (typeof this.options.ignoreElements != "function" || !this.options.ignoreElements(t)))) &&
                    (!this.options.copyStyles || !ZA(t) || !wn(t)) &&
                    A.appendChild(this.cloneNode(t, r));
            }),
            (e.prototype.cloneChildNodes = function (A, t, r) {
                for (var n = this, s = A.shadowRoot ? A.shadowRoot.firstChild : A.firstChild; s; s = s.nextSibling)
                    if (ZA(s) && vs(s) && typeof s.assignedNodes == "function") {
                        var B = s.assignedNodes();
                        B.length &&
                            B.forEach(function (i) {
                                return n.appendChildNode(t, i, r);
                            });
                    } else this.appendChildNode(t, s, r);
            }),
            (e.prototype.cloneNode = function (A, t) {
                if (ds(A)) return document.createTextNode(A.data);
                if (!A.ownerDocument) return A.cloneNode(!1);
                var r = A.ownerDocument.defaultView;
                if (r && ZA(A) && (ir(A) || ze(A))) {
                    var n = this.createElementClone(A);
                    n.style.transitionProperty = "none";
                    var s = r.getComputedStyle(A),
                        B = r.getComputedStyle(A, ":before"),
                        i = r.getComputedStyle(A, ":after");
                    this.referenceElement === A && ir(n) && (this.clonedReferenceElement = n), dr(n) && Oc(n);
                    var a = this.counters.parse(new zr(this.context, s)),
                        o = this.resolvePseudoContent(A, n, B, fe.BEFORE);
                    fn(A) && (t = !0), Qn(A) || this.cloneChildNodes(A, n, t), o && n.insertBefore(o, n.firstChild);
                    var c = this.resolvePseudoContent(A, n, i, fe.AFTER);
                    return (
                        c && n.appendChild(c),
                        this.counters.pop(a),
                        ((s && (this.options.copyStyles || ze(A)) && !Hs(A)) || t) && Nt(s, n),
                        (A.scrollTop !== 0 || A.scrollLeft !== 0) &&
                            this.scrolledElements.push([n, A.scrollLeft, A.scrollTop]),
                        (st(A) || Bt(A)) && (st(n) || Bt(n)) && (n.value = A.value),
                        n
                    );
                }
                return A.cloneNode(!1);
            }),
            (e.prototype.resolvePseudoContent = function (A, t, r, n) {
                var s = this;
                if (r) {
                    var B = r.content,
                        i = t.ownerDocument;
                    if (!(!i || !B || B === "none" || B === "-moz-alt-content" || r.display === "none")) {
                        this.counters.parse(new zr(this.context, r));
                        var a = new Co(this.context, r),
                            o = i.createElement("html2canvaspseudoelement");
                        Nt(r, o),
                            a.content.forEach(function (l) {
                                if (l.type === 0) o.appendChild(i.createTextNode(l.value));
                                else if (l.type === 22) {
                                    var g = i.createElement("img");
                                    (g.src = l.value), (g.style.opacity = "1"), o.appendChild(g);
                                } else if (l.type === 18) {
                                    if (l.name === "attr") {
                                        var w = l.values.filter(x);
                                        w.length && o.appendChild(i.createTextNode(A.getAttribute(w[0].value) || ""));
                                    } else if (l.name === "counter") {
                                        var Q = l.values.filter(jA),
                                            f = Q[0],
                                            H = Q[1];
                                        if (f && x(f)) {
                                            var d = s.counters.getCounterValue(f.value),
                                                F = H && x(H) ? rr.parse(s.context, H.value) : 3;
                                            o.appendChild(i.createTextNode(Ue(d, F, !1)));
                                        }
                                    } else if (l.name === "counters") {
                                        var L = l.values.filter(jA),
                                            f = L[0],
                                            v = L[1],
                                            H = L[2];
                                        if (f && x(f)) {
                                            var p = s.counters.getCounterValues(f.value),
                                                h = H && x(H) ? rr.parse(s.context, H.value) : 3,
                                                m = v && v.type === 0 ? v.value : "",
                                                y = p
                                                    .map(function (Y) {
                                                        return Ue(Y, h, !1);
                                                    })
                                                    .join(m);
                                            o.appendChild(i.createTextNode(y));
                                        }
                                    }
                                } else if (l.type === 20)
                                    switch (l.value) {
                                        case "open-quote":
                                            o.appendChild(i.createTextNode(jr(a.quotes, s.quoteDepth++, !0)));
                                            break;
                                        case "close-quote":
                                            o.appendChild(i.createTextNode(jr(a.quotes, --s.quoteDepth, !1)));
                                            break;
                                        default:
                                            o.appendChild(i.createTextNode(l.value));
                                    }
                            }),
                            (o.className = or + " " + cr);
                        var c = n === fe.BEFORE ? " " + or : " " + cr;
                        return ze(t) ? (t.className.baseValue += c) : (t.className += c), o;
                    }
                }
            }),
            (e.destroy = function (A) {
                return A.parentNode ? (A.parentNode.removeChild(A), !0) : !1;
            }),
            e
        );
    })(),
    fe;
(function (e) {
    (e[(e.BEFORE = 0)] = "BEFORE"), (e[(e.AFTER = 1)] = "AFTER");
})(fe || (fe = {}));
var Ic = function (e, A) {
        var t = e.createElement("iframe");
        return (
            (t.className = "html2canvas-container"),
            (t.style.visibility = "hidden"),
            (t.style.position = "fixed"),
            (t.style.left = "-10000px"),
            (t.style.top = "0px"),
            (t.style.border = "0"),
            (t.width = A.width.toString()),
            (t.height = A.height.toString()),
            (t.scrolling = "no"),
            t.setAttribute(ms, "true"),
            e.body.appendChild(t),
            t
        );
    },
    mc = function (e) {
        return new Promise(function (A) {
            if (e.complete) {
                A();
                return;
            }
            if (!e.src) {
                A();
                return;
            }
            (e.onload = A), (e.onerror = A);
        });
    },
    yc = function (e) {
        return Promise.all([].slice.call(e.images, 0).map(mc));
    },
    Lc = function (e) {
        return new Promise(function (A, t) {
            var r = e.contentWindow;
            if (!r) return t("No window assigned for iframe");
            var n = r.document;
            r.onload = e.onload = function () {
                r.onload = e.onload = null;
                var s = setInterval(function () {
                    n.body.childNodes.length > 0 && n.readyState === "complete" && (clearInterval(s), A(e));
                }, 50);
            };
        });
    },
    Kc = ["all", "d", "content"],
    Nt = function (e, A) {
        for (var t = e.length - 1; t >= 0; t--) {
            var r = e.item(t);
            Kc.indexOf(r) === -1 && A.style.setProperty(r, e.getPropertyValue(r));
        }
        return A;
    },
    bc = function (e) {
        var A = "";
        return (
            e &&
                ((A += "<!DOCTYPE "),
                e.name && (A += e.name),
                e.internalSubset && (A += e.internalSubset),
                e.publicId && (A += '"' + e.publicId + '"'),
                e.systemId && (A += '"' + e.systemId + '"'),
                (A += ">")),
            A
        );
    },
    xc = function (e, A, t) {
        e &&
            e.defaultView &&
            (A !== e.defaultView.pageXOffset || t !== e.defaultView.pageYOffset) &&
            e.defaultView.scrollTo(A, t);
    },
    Dc = function (e) {
        var A = e[0],
            t = e[1],
            r = e[2];
        (A.scrollLeft = t), (A.scrollTop = r);
    },
    Sc = ":before",
    Tc = ":after",
    or = "___html2canvas___pseudoelement_before",
    cr = "___html2canvas___pseudoelement_after",
    En = `{
    content: "" !important;
    display: none !important;
}`,
    Oc = function (e) {
        Mc(
            e,
            "." +
                or +
                Sc +
                En +
                `
         .` +
                cr +
                Tc +
                En
        );
    },
    Mc = function (e, A) {
        var t = e.ownerDocument;
        if (t) {
            var r = t.createElement("style");
            (r.textContent = A), e.appendChild(r);
        }
    },
    ys = (function () {
        function e() {}
        return (
            (e.getOrigin = function (A) {
                var t = e._link;
                return t ? ((t.href = A), (t.href = t.href), t.protocol + t.hostname + t.port) : "about:blank";
            }),
            (e.isSameOrigin = function (A) {
                return e.getOrigin(A) === e._origin;
            }),
            (e.setContext = function (A) {
                (e._link = A.document.createElement("a")), (e._origin = e.getOrigin(A.location.href));
            }),
            (e._origin = "about:blank"),
            e
        );
    })(),
    Rc = (function () {
        function e(A, t) {
            (this.context = A), (this._options = t), (this._cache = {});
        }
        return (
            (e.prototype.addImage = function (A) {
                var t = Promise.resolve();
                return (
                    this.has(A) || ((Vt(A) || kc(A)) && (this._cache[A] = this.loadImage(A)).catch(function () {})), t
                );
            }),
            (e.prototype.match = function (A) {
                return this._cache[A];
            }),
            (e.prototype.loadImage = function (A) {
                return J(this, void 0, void 0, function () {
                    var t,
                        r,
                        n,
                        s,
                        B = this;
                    return _(this, function (i) {
                        switch (i.label) {
                            case 0:
                                return (
                                    (t = ys.isSameOrigin(A)),
                                    (r = !Gt(A) && this._options.useCORS === !0 && k.SUPPORT_CORS_IMAGES && !t),
                                    (n =
                                        !Gt(A) &&
                                        !t &&
                                        !Vt(A) &&
                                        typeof this._options.proxy == "string" &&
                                        k.SUPPORT_CORS_XHR &&
                                        !r),
                                    !t && this._options.allowTaint === !1 && !Gt(A) && !Vt(A) && !n && !r
                                        ? [2]
                                        : ((s = A), n ? [4, this.proxy(s)] : [3, 2])
                                );
                            case 1:
                                (s = i.sent()), (i.label = 2);
                            case 2:
                                return (
                                    this.context.logger.debug("Added image " + A.substring(0, 256)),
                                    [
                                        4,
                                        new Promise(function (a, o) {
                                            var c = new Image();
                                            (c.onload = function () {
                                                return a(c);
                                            }),
                                                (c.onerror = o),
                                                (Pc(s) || r) && (c.crossOrigin = "anonymous"),
                                                (c.src = s),
                                                c.complete === !0 &&
                                                    setTimeout(function () {
                                                        return a(c);
                                                    }, 500),
                                                B._options.imageTimeout > 0 &&
                                                    setTimeout(function () {
                                                        return o(
                                                            "Timed out (" +
                                                                B._options.imageTimeout +
                                                                "ms) loading image"
                                                        );
                                                    }, B._options.imageTimeout);
                                        }),
                                    ]
                                );
                            case 3:
                                return [2, i.sent()];
                        }
                    });
                });
            }),
            (e.prototype.has = function (A) {
                return typeof this._cache[A] != "undefined";
            }),
            (e.prototype.keys = function () {
                return Promise.resolve(Object.keys(this._cache));
            }),
            (e.prototype.proxy = function (A) {
                var t = this,
                    r = this._options.proxy;
                if (!r) throw new Error("No proxy defined");
                var n = A.substring(0, 256);
                return new Promise(function (s, B) {
                    var i = k.SUPPORT_RESPONSE_TYPE ? "blob" : "text",
                        a = new XMLHttpRequest();
                    (a.onload = function () {
                        if (a.status === 200)
                            if (i === "text") s(a.response);
                            else {
                                var l = new FileReader();
                                l.addEventListener(
                                    "load",
                                    function () {
                                        return s(l.result);
                                    },
                                    !1
                                ),
                                    l.addEventListener(
                                        "error",
                                        function (g) {
                                            return B(g);
                                        },
                                        !1
                                    ),
                                    l.readAsDataURL(a.response);
                            }
                        else B("Failed to proxy resource " + n + " with status code " + a.status);
                    }),
                        (a.onerror = B);
                    var o = r.indexOf("?") > -1 ? "&" : "?";
                    if (
                        (a.open("GET", "" + r + o + "url=" + encodeURIComponent(A) + "&responseType=" + i),
                        i !== "text" && a instanceof XMLHttpRequest && (a.responseType = i),
                        t._options.imageTimeout)
                    ) {
                        var c = t._options.imageTimeout;
                        (a.timeout = c),
                            (a.ontimeout = function () {
                                return B("Timed out (" + c + "ms) proxying " + n);
                            });
                    }
                    a.send();
                });
            }),
            e
        );
    })(),
    Nc = /^data:image\/svg\+xml/i,
    Gc = /^data:image\/.*;base64,/i,
    Vc = /^data:image\/.*/i,
    kc = function (e) {
        return k.SUPPORT_SVG_DRAWING || !_c(e);
    },
    Gt = function (e) {
        return Vc.test(e);
    },
    Pc = function (e) {
        return Gc.test(e);
    },
    Vt = function (e) {
        return e.substr(0, 4) === "blob";
    },
    _c = function (e) {
        return e.substr(-3).toLowerCase() === "svg" || Nc.test(e);
    },
    C = (function () {
        function e(A, t) {
            (this.type = 0), (this.x = A), (this.y = t);
        }
        return (
            (e.prototype.add = function (A, t) {
                return new e(this.x + A, this.y + t);
            }),
            e
        );
    })(),
    XA = function (e, A, t) {
        return new C(e.x + (A.x - e.x) * t, e.y + (A.y - e.y) * t);
    },
    _e = (function () {
        function e(A, t, r, n) {
            (this.type = 1), (this.start = A), (this.startControl = t), (this.endControl = r), (this.end = n);
        }
        return (
            (e.prototype.subdivide = function (A, t) {
                var r = XA(this.start, this.startControl, A),
                    n = XA(this.startControl, this.endControl, A),
                    s = XA(this.endControl, this.end, A),
                    B = XA(r, n, A),
                    i = XA(n, s, A),
                    a = XA(B, i, A);
                return t ? new e(this.start, r, B, a) : new e(a, i, s, this.end);
            }),
            (e.prototype.add = function (A, t) {
                return new e(
                    this.start.add(A, t),
                    this.startControl.add(A, t),
                    this.endControl.add(A, t),
                    this.end.add(A, t)
                );
            }),
            (e.prototype.reverse = function () {
                return new e(this.end, this.endControl, this.startControl, this.start);
            }),
            e
        );
    })(),
    eA = function (e) {
        return e.type === 1;
    },
    Xc = (function () {
        function e(A) {
            var t = A.styles,
                r = A.bounds,
                n = oe(t.borderTopLeftRadius, r.width, r.height),
                s = n[0],
                B = n[1],
                i = oe(t.borderTopRightRadius, r.width, r.height),
                a = i[0],
                o = i[1],
                c = oe(t.borderBottomRightRadius, r.width, r.height),
                l = c[0],
                g = c[1],
                w = oe(t.borderBottomLeftRadius, r.width, r.height),
                Q = w[0],
                f = w[1],
                H = [];
            H.push((s + a) / r.width),
                H.push((Q + l) / r.width),
                H.push((B + f) / r.height),
                H.push((o + g) / r.height);
            var d = Math.max.apply(Math, H);
            d > 1 && ((s /= d), (B /= d), (a /= d), (o /= d), (l /= d), (g /= d), (Q /= d), (f /= d));
            var F = r.width - a,
                L = r.height - g,
                v = r.width - l,
                p = r.height - f,
                h = t.borderTopWidth,
                m = t.borderRightWidth,
                y = t.borderBottomWidth,
                E = t.borderLeftWidth,
                M = D(t.paddingTop, A.bounds.width),
                Y = D(t.paddingRight, A.bounds.width),
                j = D(t.paddingBottom, A.bounds.width),
                b = D(t.paddingLeft, A.bounds.width);
            (this.topLeftBorderDoubleOuterBox =
                s > 0 || B > 0
                    ? S(r.left + E / 3, r.top + h / 3, s - E / 3, B - h / 3, K.TOP_LEFT)
                    : new C(r.left + E / 3, r.top + h / 3)),
                (this.topRightBorderDoubleOuterBox =
                    s > 0 || B > 0
                        ? S(r.left + F, r.top + h / 3, a - m / 3, o - h / 3, K.TOP_RIGHT)
                        : new C(r.left + r.width - m / 3, r.top + h / 3)),
                (this.bottomRightBorderDoubleOuterBox =
                    l > 0 || g > 0
                        ? S(r.left + v, r.top + L, l - m / 3, g - y / 3, K.BOTTOM_RIGHT)
                        : new C(r.left + r.width - m / 3, r.top + r.height - y / 3)),
                (this.bottomLeftBorderDoubleOuterBox =
                    Q > 0 || f > 0
                        ? S(r.left + E / 3, r.top + p, Q - E / 3, f - y / 3, K.BOTTOM_LEFT)
                        : new C(r.left + E / 3, r.top + r.height - y / 3)),
                (this.topLeftBorderDoubleInnerBox =
                    s > 0 || B > 0
                        ? S(r.left + (E * 2) / 3, r.top + (h * 2) / 3, s - (E * 2) / 3, B - (h * 2) / 3, K.TOP_LEFT)
                        : new C(r.left + (E * 2) / 3, r.top + (h * 2) / 3)),
                (this.topRightBorderDoubleInnerBox =
                    s > 0 || B > 0
                        ? S(r.left + F, r.top + (h * 2) / 3, a - (m * 2) / 3, o - (h * 2) / 3, K.TOP_RIGHT)
                        : new C(r.left + r.width - (m * 2) / 3, r.top + (h * 2) / 3)),
                (this.bottomRightBorderDoubleInnerBox =
                    l > 0 || g > 0
                        ? S(r.left + v, r.top + L, l - (m * 2) / 3, g - (y * 2) / 3, K.BOTTOM_RIGHT)
                        : new C(r.left + r.width - (m * 2) / 3, r.top + r.height - (y * 2) / 3)),
                (this.bottomLeftBorderDoubleInnerBox =
                    Q > 0 || f > 0
                        ? S(r.left + (E * 2) / 3, r.top + p, Q - (E * 2) / 3, f - (y * 2) / 3, K.BOTTOM_LEFT)
                        : new C(r.left + (E * 2) / 3, r.top + r.height - (y * 2) / 3)),
                (this.topLeftBorderStroke =
                    s > 0 || B > 0
                        ? S(r.left + E / 2, r.top + h / 2, s - E / 2, B - h / 2, K.TOP_LEFT)
                        : new C(r.left + E / 2, r.top + h / 2)),
                (this.topRightBorderStroke =
                    s > 0 || B > 0
                        ? S(r.left + F, r.top + h / 2, a - m / 2, o - h / 2, K.TOP_RIGHT)
                        : new C(r.left + r.width - m / 2, r.top + h / 2)),
                (this.bottomRightBorderStroke =
                    l > 0 || g > 0
                        ? S(r.left + v, r.top + L, l - m / 2, g - y / 2, K.BOTTOM_RIGHT)
                        : new C(r.left + r.width - m / 2, r.top + r.height - y / 2)),
                (this.bottomLeftBorderStroke =
                    Q > 0 || f > 0
                        ? S(r.left + E / 2, r.top + p, Q - E / 2, f - y / 2, K.BOTTOM_LEFT)
                        : new C(r.left + E / 2, r.top + r.height - y / 2)),
                (this.topLeftBorderBox = s > 0 || B > 0 ? S(r.left, r.top, s, B, K.TOP_LEFT) : new C(r.left, r.top)),
                (this.topRightBorderBox =
                    a > 0 || o > 0 ? S(r.left + F, r.top, a, o, K.TOP_RIGHT) : new C(r.left + r.width, r.top)),
                (this.bottomRightBorderBox =
                    l > 0 || g > 0
                        ? S(r.left + v, r.top + L, l, g, K.BOTTOM_RIGHT)
                        : new C(r.left + r.width, r.top + r.height)),
                (this.bottomLeftBorderBox =
                    Q > 0 || f > 0 ? S(r.left, r.top + p, Q, f, K.BOTTOM_LEFT) : new C(r.left, r.top + r.height)),
                (this.topLeftPaddingBox =
                    s > 0 || B > 0
                        ? S(r.left + E, r.top + h, Math.max(0, s - E), Math.max(0, B - h), K.TOP_LEFT)
                        : new C(r.left + E, r.top + h)),
                (this.topRightPaddingBox =
                    a > 0 || o > 0
                        ? S(
                              r.left + Math.min(F, r.width - m),
                              r.top + h,
                              F > r.width + m ? 0 : Math.max(0, a - m),
                              Math.max(0, o - h),
                              K.TOP_RIGHT
                          )
                        : new C(r.left + r.width - m, r.top + h)),
                (this.bottomRightPaddingBox =
                    l > 0 || g > 0
                        ? S(
                              r.left + Math.min(v, r.width - E),
                              r.top + Math.min(L, r.height - y),
                              Math.max(0, l - m),
                              Math.max(0, g - y),
                              K.BOTTOM_RIGHT
                          )
                        : new C(r.left + r.width - m, r.top + r.height - y)),
                (this.bottomLeftPaddingBox =
                    Q > 0 || f > 0
                        ? S(
                              r.left + E,
                              r.top + Math.min(p, r.height - y),
                              Math.max(0, Q - E),
                              Math.max(0, f - y),
                              K.BOTTOM_LEFT
                          )
                        : new C(r.left + E, r.top + r.height - y)),
                (this.topLeftContentBox =
                    s > 0 || B > 0
                        ? S(
                              r.left + E + b,
                              r.top + h + M,
                              Math.max(0, s - (E + b)),
                              Math.max(0, B - (h + M)),
                              K.TOP_LEFT
                          )
                        : new C(r.left + E + b, r.top + h + M)),
                (this.topRightContentBox =
                    a > 0 || o > 0
                        ? S(
                              r.left + Math.min(F, r.width + E + b),
                              r.top + h + M,
                              F > r.width + E + b ? 0 : a - E + b,
                              o - (h + M),
                              K.TOP_RIGHT
                          )
                        : new C(r.left + r.width - (m + Y), r.top + h + M)),
                (this.bottomRightContentBox =
                    l > 0 || g > 0
                        ? S(
                              r.left + Math.min(v, r.width - (E + b)),
                              r.top + Math.min(L, r.height + h + M),
                              Math.max(0, l - (m + Y)),
                              g - (y + j),
                              K.BOTTOM_RIGHT
                          )
                        : new C(r.left + r.width - (m + Y), r.top + r.height - (y + j))),
                (this.bottomLeftContentBox =
                    Q > 0 || f > 0
                        ? S(r.left + E + b, r.top + p, Math.max(0, Q - (E + b)), f - (y + j), K.BOTTOM_LEFT)
                        : new C(r.left + E + b, r.top + r.height - (y + j)));
        }
        return e;
    })(),
    K;
(function (e) {
    (e[(e.TOP_LEFT = 0)] = "TOP_LEFT"),
        (e[(e.TOP_RIGHT = 1)] = "TOP_RIGHT"),
        (e[(e.BOTTOM_RIGHT = 2)] = "BOTTOM_RIGHT"),
        (e[(e.BOTTOM_LEFT = 3)] = "BOTTOM_LEFT");
})(K || (K = {}));
var S = function (e, A, t, r, n) {
        var s = 4 * ((Math.sqrt(2) - 1) / 3),
            B = t * s,
            i = r * s,
            a = e + t,
            o = A + r;
        switch (n) {
            case K.TOP_LEFT:
                return new _e(new C(e, o), new C(e, o - i), new C(a - B, A), new C(a, A));
            case K.TOP_RIGHT:
                return new _e(new C(e, A), new C(e + B, A), new C(a, o - i), new C(a, o));
            case K.BOTTOM_RIGHT:
                return new _e(new C(a, A), new C(a, A + i), new C(e + B, o), new C(e, o));
            case K.BOTTOM_LEFT:
            default:
                return new _e(new C(a, o), new C(a - B, o), new C(e, A + i), new C(e, A));
        }
    },
    it = function (e) {
        return [e.topLeftBorderBox, e.topRightBorderBox, e.bottomRightBorderBox, e.bottomLeftBorderBox];
    },
    Jc = function (e) {
        return [e.topLeftContentBox, e.topRightContentBox, e.bottomRightContentBox, e.bottomLeftContentBox];
    },
    at = function (e) {
        return [e.topLeftPaddingBox, e.topRightPaddingBox, e.bottomRightPaddingBox, e.bottomLeftPaddingBox];
    },
    Yc = (function () {
        function e(A, t, r) {
            (this.offsetX = A), (this.offsetY = t), (this.matrix = r), (this.type = 0), (this.target = 6);
        }
        return e;
    })(),
    Xe = (function () {
        function e(A, t) {
            (this.path = A), (this.target = t), (this.type = 1);
        }
        return e;
    })(),
    Wc = (function () {
        function e(A) {
            (this.opacity = A), (this.type = 2), (this.target = 6);
        }
        return e;
    })(),
    Zc = function (e) {
        return e.type === 0;
    },
    Ls = function (e) {
        return e.type === 1;
    },
    qc = function (e) {
        return e.type === 2;
    },
    Hn = function (e, A) {
        return e.length === A.length
            ? e.some(function (t, r) {
                  return t === A[r];
              })
            : !1;
    },
    jc = function (e, A, t, r, n) {
        return e.map(function (s, B) {
            switch (B) {
                case 0:
                    return s.add(A, t);
                case 1:
                    return s.add(A + r, t);
                case 2:
                    return s.add(A + r, t + n);
                case 3:
                    return s.add(A, t + n);
            }
            return s;
        });
    },
    Ks = (function () {
        function e(A) {
            (this.element = A),
                (this.inlineLevel = []),
                (this.nonInlineLevel = []),
                (this.negativeZIndex = []),
                (this.zeroOrAutoZIndexOrTransformedOrOpacity = []),
                (this.positiveZIndex = []),
                (this.nonPositionedFloats = []),
                (this.nonPositionedInlineLevel = []);
        }
        return e;
    })(),
    bs = (function () {
        function e(A, t) {
            if (
                ((this.container = A),
                (this.parent = t),
                (this.effects = []),
                (this.curves = new Xc(this.container)),
                this.container.styles.opacity < 1 && this.effects.push(new Wc(this.container.styles.opacity)),
                this.container.styles.transform !== null)
            ) {
                var r = this.container.bounds.left + this.container.styles.transformOrigin[0].number,
                    n = this.container.bounds.top + this.container.styles.transformOrigin[1].number,
                    s = this.container.styles.transform;
                this.effects.push(new Yc(r, n, s));
            }
            if (this.container.styles.overflowX !== 0) {
                var B = it(this.curves),
                    i = at(this.curves);
                Hn(B, i)
                    ? this.effects.push(new Xe(B, 6))
                    : (this.effects.push(new Xe(B, 2)), this.effects.push(new Xe(i, 4)));
            }
        }
        return (
            (e.prototype.getEffects = function (A) {
                for (
                    var t = [2, 3].indexOf(this.container.styles.position) === -1,
                        r = this.parent,
                        n = this.effects.slice(0);
                    r;

                ) {
                    var s = r.effects.filter(function (a) {
                        return !Ls(a);
                    });
                    if (t || r.container.styles.position !== 0 || !r.parent) {
                        if (
                            (n.unshift.apply(n, s),
                            (t = [2, 3].indexOf(r.container.styles.position) === -1),
                            r.container.styles.overflowX !== 0)
                        ) {
                            var B = it(r.curves),
                                i = at(r.curves);
                            Hn(B, i) || n.unshift(new Xe(i, 6));
                        }
                    } else n.unshift.apply(n, s);
                    r = r.parent;
                }
                return n.filter(function (a) {
                    return N(a.target, A);
                });
            }),
            e
        );
    })(),
    lr = function (e, A, t, r) {
        e.container.elements.forEach(function (n) {
            var s = N(n.flags, 4),
                B = N(n.flags, 2),
                i = new bs(n, e);
            N(n.styles.display, 2048) && r.push(i);
            var a = N(n.flags, 8) ? [] : r;
            if (s || B) {
                var o = s || n.styles.isPositioned() ? t : A,
                    c = new Ks(i);
                if (n.styles.isPositioned() || n.styles.opacity < 1 || n.styles.isTransformed()) {
                    var l = n.styles.zIndex.order;
                    if (l < 0) {
                        var g = 0;
                        o.negativeZIndex.some(function (Q, f) {
                            return l > Q.element.container.styles.zIndex.order ? ((g = f), !1) : g > 0;
                        }),
                            o.negativeZIndex.splice(g, 0, c);
                    } else if (l > 0) {
                        var w = 0;
                        o.positiveZIndex.some(function (Q, f) {
                            return l >= Q.element.container.styles.zIndex.order ? ((w = f + 1), !1) : w > 0;
                        }),
                            o.positiveZIndex.splice(w, 0, c);
                    } else o.zeroOrAutoZIndexOrTransformedOrOpacity.push(c);
                } else n.styles.isFloating() ? o.nonPositionedFloats.push(c) : o.nonPositionedInlineLevel.push(c);
                lr(i, c, s ? c : t, a);
            } else n.styles.isInlineLevel() ? A.inlineLevel.push(i) : A.nonInlineLevel.push(i), lr(i, A, t, a);
            N(n.flags, 8) && xs(n, a);
        });
    },
    xs = function (e, A) {
        for (var t = e instanceof Br ? e.start : 1, r = e instanceof Br ? e.reversed : !1, n = 0; n < A.length; n++) {
            var s = A[n];
            s.container instanceof ws &&
                typeof s.container.value == "number" &&
                s.container.value !== 0 &&
                (t = s.container.value),
                (s.listValue = Ue(t, s.container.styles.listStyleType, !0)),
                (t += r ? -1 : 1);
        }
    },
    zc = function (e) {
        var A = new bs(e, null),
            t = new Ks(A),
            r = [];
        return lr(A, t, t, r), xs(A.container, r), t;
    },
    vn = function (e, A) {
        switch (A) {
            case 0:
                return rA(e.topLeftBorderBox, e.topLeftPaddingBox, e.topRightBorderBox, e.topRightPaddingBox);
            case 1:
                return rA(e.topRightBorderBox, e.topRightPaddingBox, e.bottomRightBorderBox, e.bottomRightPaddingBox);
            case 2:
                return rA(
                    e.bottomRightBorderBox,
                    e.bottomRightPaddingBox,
                    e.bottomLeftBorderBox,
                    e.bottomLeftPaddingBox
                );
            case 3:
            default:
                return rA(e.bottomLeftBorderBox, e.bottomLeftPaddingBox, e.topLeftBorderBox, e.topLeftPaddingBox);
        }
    },
    $c = function (e, A) {
        switch (A) {
            case 0:
                return rA(
                    e.topLeftBorderBox,
                    e.topLeftBorderDoubleOuterBox,
                    e.topRightBorderBox,
                    e.topRightBorderDoubleOuterBox
                );
            case 1:
                return rA(
                    e.topRightBorderBox,
                    e.topRightBorderDoubleOuterBox,
                    e.bottomRightBorderBox,
                    e.bottomRightBorderDoubleOuterBox
                );
            case 2:
                return rA(
                    e.bottomRightBorderBox,
                    e.bottomRightBorderDoubleOuterBox,
                    e.bottomLeftBorderBox,
                    e.bottomLeftBorderDoubleOuterBox
                );
            case 3:
            default:
                return rA(
                    e.bottomLeftBorderBox,
                    e.bottomLeftBorderDoubleOuterBox,
                    e.topLeftBorderBox,
                    e.topLeftBorderDoubleOuterBox
                );
        }
    },
    Al = function (e, A) {
        switch (A) {
            case 0:
                return rA(
                    e.topLeftBorderDoubleInnerBox,
                    e.topLeftPaddingBox,
                    e.topRightBorderDoubleInnerBox,
                    e.topRightPaddingBox
                );
            case 1:
                return rA(
                    e.topRightBorderDoubleInnerBox,
                    e.topRightPaddingBox,
                    e.bottomRightBorderDoubleInnerBox,
                    e.bottomRightPaddingBox
                );
            case 2:
                return rA(
                    e.bottomRightBorderDoubleInnerBox,
                    e.bottomRightPaddingBox,
                    e.bottomLeftBorderDoubleInnerBox,
                    e.bottomLeftPaddingBox
                );
            case 3:
            default:
                return rA(
                    e.bottomLeftBorderDoubleInnerBox,
                    e.bottomLeftPaddingBox,
                    e.topLeftBorderDoubleInnerBox,
                    e.topLeftPaddingBox
                );
        }
    },
    el = function (e, A) {
        switch (A) {
            case 0:
                return Je(e.topLeftBorderStroke, e.topRightBorderStroke);
            case 1:
                return Je(e.topRightBorderStroke, e.bottomRightBorderStroke);
            case 2:
                return Je(e.bottomRightBorderStroke, e.bottomLeftBorderStroke);
            case 3:
            default:
                return Je(e.bottomLeftBorderStroke, e.topLeftBorderStroke);
        }
    },
    Je = function (e, A) {
        var t = [];
        return eA(e) ? t.push(e.subdivide(0.5, !1)) : t.push(e), eA(A) ? t.push(A.subdivide(0.5, !0)) : t.push(A), t;
    },
    rA = function (e, A, t, r) {
        var n = [];
        return (
            eA(e) ? n.push(e.subdivide(0.5, !1)) : n.push(e),
            eA(t) ? n.push(t.subdivide(0.5, !0)) : n.push(t),
            eA(r) ? n.push(r.subdivide(0.5, !0).reverse()) : n.push(r),
            eA(A) ? n.push(A.subdivide(0.5, !1).reverse()) : n.push(A),
            n
        );
    },
    Ds = function (e) {
        var A = e.bounds,
            t = e.styles;
        return A.add(
            t.borderLeftWidth,
            t.borderTopWidth,
            -(t.borderRightWidth + t.borderLeftWidth),
            -(t.borderTopWidth + t.borderBottomWidth)
        );
    },
    ot = function (e) {
        var A = e.styles,
            t = e.bounds,
            r = D(A.paddingLeft, t.width),
            n = D(A.paddingRight, t.width),
            s = D(A.paddingTop, t.width),
            B = D(A.paddingBottom, t.width);
        return t.add(
            r + A.borderLeftWidth,
            s + A.borderTopWidth,
            -(A.borderRightWidth + A.borderLeftWidth + r + n),
            -(A.borderTopWidth + A.borderBottomWidth + s + B)
        );
    },
    tl = function (e, A) {
        return e === 0 ? A.bounds : e === 2 ? ot(A) : Ds(A);
    },
    rl = function (e, A) {
        return e === 0 ? A.bounds : e === 2 ? ot(A) : Ds(A);
    },
    kt = function (e, A, t) {
        var r = tl(WA(e.styles.backgroundOrigin, A), e),
            n = rl(WA(e.styles.backgroundClip, A), e),
            s = nl(WA(e.styles.backgroundSize, A), t, r),
            B = s[0],
            i = s[1],
            a = oe(WA(e.styles.backgroundPosition, A), r.width - B, r.height - i),
            o = sl(WA(e.styles.backgroundRepeat, A), a, s, r, n),
            c = Math.round(r.left + a[0]),
            l = Math.round(r.top + a[1]);
        return [o, c, l, B, i];
    },
    JA = function (e) {
        return x(e) && e.value === qA.AUTO;
    },
    Ye = function (e) {
        return typeof e == "number";
    },
    nl = function (e, A, t) {
        var r = A[0],
            n = A[1],
            s = A[2],
            B = e[0],
            i = e[1];
        if (!B) return [0, 0];
        if (R(B) && i && R(i)) return [D(B, t.width), D(i, t.height)];
        var a = Ye(s);
        if (x(B) && (B.value === qA.CONTAIN || B.value === qA.COVER)) {
            if (Ye(s)) {
                var o = t.width / t.height;
                return o < s != (B.value === qA.COVER) ? [t.width, t.width / s] : [t.height * s, t.height];
            }
            return [t.width, t.height];
        }
        var c = Ye(r),
            l = Ye(n),
            g = c || l;
        if (JA(B) && (!i || JA(i))) {
            if (c && l) return [r, n];
            if (!a && !g) return [t.width, t.height];
            if (g && a) {
                var w = c ? r : n * s,
                    Q = l ? n : r / s;
                return [w, Q];
            }
            var f = c ? r : t.width,
                H = l ? n : t.height;
            return [f, H];
        }
        if (a) {
            var d = 0,
                F = 0;
            return (
                R(B) ? (d = D(B, t.width)) : R(i) && (F = D(i, t.height)),
                JA(B) ? (d = F * s) : (!i || JA(i)) && (F = d / s),
                [d, F]
            );
        }
        var L = null,
            v = null;
        if (
            (R(B) ? (L = D(B, t.width)) : i && R(i) && (v = D(i, t.height)),
            L !== null && (!i || JA(i)) && (v = c && l ? (L / r) * n : t.height),
            v !== null && JA(B) && (L = c && l ? (v / n) * r : t.width),
            L !== null && v !== null)
        )
            return [L, v];
        throw new Error("Unable to calculate background-size for element");
    },
    WA = function (e, A) {
        var t = e[A];
        return typeof t == "undefined" ? e[0] : t;
    },
    sl = function (e, A, t, r, n) {
        var s = A[0],
            B = A[1],
            i = t[0],
            a = t[1];
        switch (e) {
            case 2:
                return [
                    new C(Math.round(r.left), Math.round(r.top + B)),
                    new C(Math.round(r.left + r.width), Math.round(r.top + B)),
                    new C(Math.round(r.left + r.width), Math.round(a + r.top + B)),
                    new C(Math.round(r.left), Math.round(a + r.top + B)),
                ];
            case 3:
                return [
                    new C(Math.round(r.left + s), Math.round(r.top)),
                    new C(Math.round(r.left + s + i), Math.round(r.top)),
                    new C(Math.round(r.left + s + i), Math.round(r.height + r.top)),
                    new C(Math.round(r.left + s), Math.round(r.height + r.top)),
                ];
            case 1:
                return [
                    new C(Math.round(r.left + s), Math.round(r.top + B)),
                    new C(Math.round(r.left + s + i), Math.round(r.top + B)),
                    new C(Math.round(r.left + s + i), Math.round(r.top + B + a)),
                    new C(Math.round(r.left + s), Math.round(r.top + B + a)),
                ];
            default:
                return [
                    new C(Math.round(n.left), Math.round(n.top)),
                    new C(Math.round(n.left + n.width), Math.round(n.top)),
                    new C(Math.round(n.left + n.width), Math.round(n.height + n.top)),
                    new C(Math.round(n.left), Math.round(n.height + n.top)),
                ];
        }
    },
    Bl = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7",
    In = "Hidden Text",
    il = (function () {
        function e(A) {
            (this._data = {}), (this._document = A);
        }
        return (
            (e.prototype.parseMetrics = function (A, t) {
                var r = this._document.createElement("div"),
                    n = this._document.createElement("img"),
                    s = this._document.createElement("span"),
                    B = this._document.body;
                (r.style.visibility = "hidden"),
                    (r.style.fontFamily = A),
                    (r.style.fontSize = t),
                    (r.style.margin = "0"),
                    (r.style.padding = "0"),
                    (r.style.whiteSpace = "nowrap"),
                    B.appendChild(r),
                    (n.src = Bl),
                    (n.width = 1),
                    (n.height = 1),
                    (n.style.margin = "0"),
                    (n.style.padding = "0"),
                    (n.style.verticalAlign = "baseline"),
                    (s.style.fontFamily = A),
                    (s.style.fontSize = t),
                    (s.style.margin = "0"),
                    (s.style.padding = "0"),
                    s.appendChild(this._document.createTextNode(In)),
                    r.appendChild(s),
                    r.appendChild(n);
                var i = n.offsetTop - s.offsetTop + 2;
                r.removeChild(s),
                    r.appendChild(this._document.createTextNode(In)),
                    (r.style.lineHeight = "normal"),
                    (n.style.verticalAlign = "super");
                var a = n.offsetTop - r.offsetTop + 2;
                return B.removeChild(r), { baseline: i, middle: a };
            }),
            (e.prototype.getMetrics = function (A, t) {
                var r = A + " " + t;
                return typeof this._data[r] == "undefined" && (this._data[r] = this.parseMetrics(A, t)), this._data[r];
            }),
            e
        );
    })(),
    Ss = (function () {
        function e(A, t) {
            (this.context = A), (this.options = t);
        }
        return e;
    })(),
    al = 1e4,
    ol = (function (e) {
        sA(A, e);
        function A(t, r) {
            var n = e.call(this, t, r) || this;
            return (
                (n._activeEffects = []),
                (n.canvas = r.canvas ? r.canvas : document.createElement("canvas")),
                (n.ctx = n.canvas.getContext("2d")),
                r.canvas ||
                    ((n.canvas.width = Math.floor(r.width * r.scale)),
                    (n.canvas.height = Math.floor(r.height * r.scale)),
                    (n.canvas.style.width = r.width + "px"),
                    (n.canvas.style.height = r.height + "px")),
                (n.fontMetrics = new il(document)),
                n.ctx.scale(n.options.scale, n.options.scale),
                n.ctx.translate(-r.x, -r.y),
                (n.ctx.textBaseline = "bottom"),
                (n._activeEffects = []),
                n.context.logger.debug(
                    "Canvas renderer initialized (" + r.width + "x" + r.height + ") with scale " + r.scale
                ),
                n
            );
        }
        return (
            (A.prototype.applyEffects = function (t) {
                for (var r = this; this._activeEffects.length; ) this.popEffect();
                t.forEach(function (n) {
                    return r.applyEffect(n);
                });
            }),
            (A.prototype.applyEffect = function (t) {
                this.ctx.save(),
                    qc(t) && (this.ctx.globalAlpha = t.opacity),
                    Zc(t) &&
                        (this.ctx.translate(t.offsetX, t.offsetY),
                        this.ctx.transform(
                            t.matrix[0],
                            t.matrix[1],
                            t.matrix[2],
                            t.matrix[3],
                            t.matrix[4],
                            t.matrix[5]
                        ),
                        this.ctx.translate(-t.offsetX, -t.offsetY)),
                    Ls(t) && (this.path(t.path), this.ctx.clip()),
                    this._activeEffects.push(t);
            }),
            (A.prototype.popEffect = function () {
                this._activeEffects.pop(), this.ctx.restore();
            }),
            (A.prototype.renderStack = function (t) {
                return J(this, void 0, void 0, function () {
                    var r;
                    return _(this, function (n) {
                        switch (n.label) {
                            case 0:
                                return (
                                    (r = t.element.container.styles),
                                    r.isVisible() ? [4, this.renderStackContent(t)] : [3, 2]
                                );
                            case 1:
                                n.sent(), (n.label = 2);
                            case 2:
                                return [2];
                        }
                    });
                });
            }),
            (A.prototype.renderNode = function (t) {
                return J(this, void 0, void 0, function () {
                    return _(this, function (r) {
                        switch (r.label) {
                            case 0:
                                if (N(t.container.flags, 16)) debugger;
                                return t.container.styles.isVisible()
                                    ? [4, this.renderNodeBackgroundAndBorders(t)]
                                    : [3, 3];
                            case 1:
                                return r.sent(), [4, this.renderNodeContent(t)];
                            case 2:
                                r.sent(), (r.label = 3);
                            case 3:
                                return [2];
                        }
                    });
                });
            }),
            (A.prototype.renderTextWithLetterSpacing = function (t, r, n) {
                var s = this;
                if (r === 0) this.ctx.fillText(t.text, t.bounds.left, t.bounds.top + n);
                else {
                    var B = Ur(t.text);
                    B.reduce(function (i, a) {
                        return s.ctx.fillText(a, i, t.bounds.top + n), i + s.ctx.measureText(a).width;
                    }, t.bounds.left);
                }
            }),
            (A.prototype.createFontStyle = function (t) {
                var r = t.fontVariant
                        .filter(function (B) {
                            return B === "normal" || B === "small-caps";
                        })
                        .join(""),
                    n = Ql(t.fontFamily).join(", "),
                    s = de(t.fontSize) ? "" + t.fontSize.number + t.fontSize.unit : t.fontSize.number + "px";
                return [[t.fontStyle, r, t.fontWeight, s, n].join(" "), n, s];
            }),
            (A.prototype.renderTextNode = function (t, r) {
                return J(this, void 0, void 0, function () {
                    var n,
                        s,
                        B,
                        i,
                        a,
                        o,
                        c,
                        l,
                        g = this;
                    return _(this, function (w) {
                        return (
                            (n = this.createFontStyle(r)),
                            (s = n[0]),
                            (B = n[1]),
                            (i = n[2]),
                            (this.ctx.font = s),
                            (this.ctx.direction = r.direction === 1 ? "rtl" : "ltr"),
                            (this.ctx.textAlign = "left"),
                            (this.ctx.textBaseline = "alphabetic"),
                            (a = this.fontMetrics.getMetrics(B, i)),
                            (o = a.baseline),
                            (c = a.middle),
                            (l = r.paintOrder),
                            t.textBounds.forEach(function (Q) {
                                l.forEach(function (f) {
                                    switch (f) {
                                        case 0:
                                            (g.ctx.fillStyle = G(r.color)),
                                                g.renderTextWithLetterSpacing(Q, r.letterSpacing, o);
                                            var H = r.textShadow;
                                            H.length &&
                                                Q.text.trim().length &&
                                                (H.slice(0)
                                                    .reverse()
                                                    .forEach(function (d) {
                                                        (g.ctx.shadowColor = G(d.color)),
                                                            (g.ctx.shadowOffsetX = d.offsetX.number * g.options.scale),
                                                            (g.ctx.shadowOffsetY = d.offsetY.number * g.options.scale),
                                                            (g.ctx.shadowBlur = d.blur.number),
                                                            g.renderTextWithLetterSpacing(Q, r.letterSpacing, o);
                                                    }),
                                                (g.ctx.shadowColor = ""),
                                                (g.ctx.shadowOffsetX = 0),
                                                (g.ctx.shadowOffsetY = 0),
                                                (g.ctx.shadowBlur = 0)),
                                                r.textDecorationLine.length &&
                                                    ((g.ctx.fillStyle = G(r.textDecorationColor || r.color)),
                                                    r.textDecorationLine.forEach(function (d) {
                                                        switch (d) {
                                                            case 1:
                                                                g.ctx.fillRect(
                                                                    Q.bounds.left,
                                                                    Math.round(Q.bounds.top + o),
                                                                    Q.bounds.width,
                                                                    1
                                                                );
                                                                break;
                                                            case 2:
                                                                g.ctx.fillRect(
                                                                    Q.bounds.left,
                                                                    Math.round(Q.bounds.top),
                                                                    Q.bounds.width,
                                                                    1
                                                                );
                                                                break;
                                                            case 3:
                                                                g.ctx.fillRect(
                                                                    Q.bounds.left,
                                                                    Math.ceil(Q.bounds.top + c),
                                                                    Q.bounds.width,
                                                                    1
                                                                );
                                                                break;
                                                        }
                                                    }));
                                            break;
                                        case 1:
                                            r.webkitTextStrokeWidth &&
                                                Q.text.trim().length &&
                                                ((g.ctx.strokeStyle = G(r.webkitTextStrokeColor)),
                                                (g.ctx.lineWidth = r.webkitTextStrokeWidth),
                                                (g.ctx.lineJoin = window.chrome ? "miter" : "round"),
                                                g.ctx.strokeText(Q.text, Q.bounds.left, Q.bounds.top + o)),
                                                (g.ctx.strokeStyle = ""),
                                                (g.ctx.lineWidth = 0),
                                                (g.ctx.lineJoin = "miter");
                                            break;
                                    }
                                });
                            }),
                            [2]
                        );
                    });
                });
            }),
            (A.prototype.renderReplacedElement = function (t, r, n) {
                if (n && t.intrinsicWidth > 0 && t.intrinsicHeight > 0) {
                    var s = ot(t),
                        B = at(r);
                    this.path(B),
                        this.ctx.save(),
                        this.ctx.clip(),
                        this.ctx.drawImage(
                            n,
                            0,
                            0,
                            t.intrinsicWidth,
                            t.intrinsicHeight,
                            s.left,
                            s.top,
                            s.width,
                            s.height
                        ),
                        this.ctx.restore();
                }
            }),
            (A.prototype.renderNodeContent = function (t) {
                return J(this, void 0, void 0, function () {
                    var r, n, s, B, i, a, F, F, o, c, l, g, v, w, Q, p, f, H, d, F, L, v, p;
                    return _(this, function (h) {
                        switch (h.label) {
                            case 0:
                                this.applyEffects(t.getEffects(4)),
                                    (r = t.container),
                                    (n = t.curves),
                                    (s = r.styles),
                                    (B = 0),
                                    (i = r.textNodes),
                                    (h.label = 1);
                            case 1:
                                return B < i.length ? ((a = i[B]), [4, this.renderTextNode(a, s)]) : [3, 4];
                            case 2:
                                h.sent(), (h.label = 3);
                            case 3:
                                return B++, [3, 1];
                            case 4:
                                if (!(r instanceof gs)) return [3, 8];
                                h.label = 5;
                            case 5:
                                return h.trys.push([5, 7, , 8]), [4, this.context.cache.match(r.src)];
                            case 6:
                                return (F = h.sent()), this.renderReplacedElement(r, n, F), [3, 8];
                            case 7:
                                return h.sent(), this.context.logger.error("Error loading image " + r.src), [3, 8];
                            case 8:
                                if ((r instanceof us && this.renderReplacedElement(r, n, r.canvas), !(r instanceof Qs)))
                                    return [3, 12];
                                h.label = 9;
                            case 9:
                                return h.trys.push([9, 11, , 12]), [4, this.context.cache.match(r.svg)];
                            case 10:
                                return (F = h.sent()), this.renderReplacedElement(r, n, F), [3, 12];
                            case 11:
                                return (
                                    h.sent(),
                                    this.context.logger.error("Error loading svg " + r.svg.substring(0, 255)),
                                    [3, 12]
                                );
                            case 12:
                                return r instanceof hs && r.tree
                                    ? ((o = new A(this.context, {
                                          scale: this.options.scale,
                                          backgroundColor: r.backgroundColor,
                                          x: 0,
                                          y: 0,
                                          width: r.width,
                                          height: r.height,
                                      })),
                                      [4, o.render(r.tree)])
                                    : [3, 14];
                            case 13:
                                (c = h.sent()),
                                    r.width &&
                                        r.height &&
                                        this.ctx.drawImage(
                                            c,
                                            0,
                                            0,
                                            r.width,
                                            r.height,
                                            r.bounds.left,
                                            r.bounds.top,
                                            r.bounds.width,
                                            r.bounds.height
                                        ),
                                    (h.label = 14);
                            case 14:
                                if (
                                    (r instanceof Fr &&
                                        ((l = Math.min(r.bounds.width, r.bounds.height)),
                                        r.type === rt
                                            ? r.checked &&
                                              (this.ctx.save(),
                                              this.path([
                                                  new C(r.bounds.left + l * 0.39363, r.bounds.top + l * 0.79),
                                                  new C(r.bounds.left + l * 0.16, r.bounds.top + l * 0.5549),
                                                  new C(r.bounds.left + l * 0.27347, r.bounds.top + l * 0.44071),
                                                  new C(r.bounds.left + l * 0.39694, r.bounds.top + l * 0.5649),
                                                  new C(r.bounds.left + l * 0.72983, r.bounds.top + l * 0.23),
                                                  new C(r.bounds.left + l * 0.84, r.bounds.top + l * 0.34085),
                                                  new C(r.bounds.left + l * 0.39363, r.bounds.top + l * 0.79),
                                              ]),
                                              (this.ctx.fillStyle = G(un)),
                                              this.ctx.fill(),
                                              this.ctx.restore())
                                            : r.type === nt &&
                                              r.checked &&
                                              (this.ctx.save(),
                                              this.ctx.beginPath(),
                                              this.ctx.arc(
                                                  r.bounds.left + l / 2,
                                                  r.bounds.top + l / 2,
                                                  l / 4,
                                                  0,
                                                  Math.PI * 2,
                                                  !0
                                              ),
                                              (this.ctx.fillStyle = G(un)),
                                              this.ctx.fill(),
                                              this.ctx.restore())),
                                    cl(r) && r.value.length)
                                ) {
                                    switch (
                                        ((g = this.createFontStyle(s)),
                                        (v = g[0]),
                                        (w = g[1]),
                                        (Q = this.fontMetrics.getMetrics(v, w).baseline),
                                        (this.ctx.font = v),
                                        (this.ctx.fillStyle = G(s.color)),
                                        (this.ctx.textBaseline = "alphabetic"),
                                        (this.ctx.textAlign = gl(r.styles.textAlign)),
                                        (p = ot(r)),
                                        (f = 0),
                                        r.styles.textAlign)
                                    ) {
                                        case 1:
                                            f += p.width / 2;
                                            break;
                                        case 2:
                                            f += p.width;
                                            break;
                                    }
                                    (H = p.add(f, 0, 0, -p.height / 2 + 1)),
                                        this.ctx.save(),
                                        this.path([
                                            new C(p.left, p.top),
                                            new C(p.left + p.width, p.top),
                                            new C(p.left + p.width, p.top + p.height),
                                            new C(p.left, p.top + p.height),
                                        ]),
                                        this.ctx.clip(),
                                        this.renderTextWithLetterSpacing(new we(r.value, H), s.letterSpacing, Q),
                                        this.ctx.restore(),
                                        (this.ctx.textBaseline = "alphabetic"),
                                        (this.ctx.textAlign = "left");
                                }
                                if (!N(r.styles.display, 2048)) return [3, 20];
                                if (r.styles.listStyleImage === null) return [3, 19];
                                if (((d = r.styles.listStyleImage), d.type !== 0)) return [3, 18];
                                (F = void 0), (L = d.url), (h.label = 15);
                            case 15:
                                return h.trys.push([15, 17, , 18]), [4, this.context.cache.match(L)];
                            case 16:
                                return (
                                    (F = h.sent()),
                                    this.ctx.drawImage(F, r.bounds.left - (F.width + 10), r.bounds.top),
                                    [3, 18]
                                );
                            case 17:
                                return (
                                    h.sent(), this.context.logger.error("Error loading list-style-image " + L), [3, 18]
                                );
                            case 18:
                                return [3, 20];
                            case 19:
                                t.listValue &&
                                    r.styles.listStyleType !== -1 &&
                                    ((v = this.createFontStyle(s)[0]),
                                    (this.ctx.font = v),
                                    (this.ctx.fillStyle = G(s.color)),
                                    (this.ctx.textBaseline = "middle"),
                                    (this.ctx.textAlign = "right"),
                                    (p = new fA(
                                        r.bounds.left,
                                        r.bounds.top + D(r.styles.paddingTop, r.bounds.width),
                                        r.bounds.width,
                                        Zr(s.lineHeight, s.fontSize.number) / 2 + 1
                                    )),
                                    this.renderTextWithLetterSpacing(
                                        new we(t.listValue, p),
                                        s.letterSpacing,
                                        Zr(s.lineHeight, s.fontSize.number) / 2 + 2
                                    ),
                                    (this.ctx.textBaseline = "bottom"),
                                    (this.ctx.textAlign = "left")),
                                    (h.label = 20);
                            case 20:
                                return [2];
                        }
                    });
                });
            }),
            (A.prototype.renderStackContent = function (t) {
                return J(this, void 0, void 0, function () {
                    var r, n, d, s, B, d, i, a, d, o, c, d, l, g, d, w, Q, d, f, H, d;
                    return _(this, function (F) {
                        switch (F.label) {
                            case 0:
                                if (N(t.element.container.flags, 16)) debugger;
                                return [4, this.renderNodeBackgroundAndBorders(t.element)];
                            case 1:
                                F.sent(), (r = 0), (n = t.negativeZIndex), (F.label = 2);
                            case 2:
                                return r < n.length ? ((d = n[r]), [4, this.renderStack(d)]) : [3, 5];
                            case 3:
                                F.sent(), (F.label = 4);
                            case 4:
                                return r++, [3, 2];
                            case 5:
                                return [4, this.renderNodeContent(t.element)];
                            case 6:
                                F.sent(), (s = 0), (B = t.nonInlineLevel), (F.label = 7);
                            case 7:
                                return s < B.length ? ((d = B[s]), [4, this.renderNode(d)]) : [3, 10];
                            case 8:
                                F.sent(), (F.label = 9);
                            case 9:
                                return s++, [3, 7];
                            case 10:
                                (i = 0), (a = t.nonPositionedFloats), (F.label = 11);
                            case 11:
                                return i < a.length ? ((d = a[i]), [4, this.renderStack(d)]) : [3, 14];
                            case 12:
                                F.sent(), (F.label = 13);
                            case 13:
                                return i++, [3, 11];
                            case 14:
                                (o = 0), (c = t.nonPositionedInlineLevel), (F.label = 15);
                            case 15:
                                return o < c.length ? ((d = c[o]), [4, this.renderStack(d)]) : [3, 18];
                            case 16:
                                F.sent(), (F.label = 17);
                            case 17:
                                return o++, [3, 15];
                            case 18:
                                (l = 0), (g = t.inlineLevel), (F.label = 19);
                            case 19:
                                return l < g.length ? ((d = g[l]), [4, this.renderNode(d)]) : [3, 22];
                            case 20:
                                F.sent(), (F.label = 21);
                            case 21:
                                return l++, [3, 19];
                            case 22:
                                (w = 0), (Q = t.zeroOrAutoZIndexOrTransformedOrOpacity), (F.label = 23);
                            case 23:
                                return w < Q.length ? ((d = Q[w]), [4, this.renderStack(d)]) : [3, 26];
                            case 24:
                                F.sent(), (F.label = 25);
                            case 25:
                                return w++, [3, 23];
                            case 26:
                                (f = 0), (H = t.positiveZIndex), (F.label = 27);
                            case 27:
                                return f < H.length ? ((d = H[f]), [4, this.renderStack(d)]) : [3, 30];
                            case 28:
                                F.sent(), (F.label = 29);
                            case 29:
                                return f++, [3, 27];
                            case 30:
                                return [2];
                        }
                    });
                });
            }),
            (A.prototype.mask = function (t) {
                this.ctx.beginPath(),
                    this.ctx.moveTo(0, 0),
                    this.ctx.lineTo(this.canvas.width, 0),
                    this.ctx.lineTo(this.canvas.width, this.canvas.height),
                    this.ctx.lineTo(0, this.canvas.height),
                    this.ctx.lineTo(0, 0),
                    this.formatPath(t.slice(0).reverse()),
                    this.ctx.closePath();
            }),
            (A.prototype.path = function (t) {
                this.ctx.beginPath(), this.formatPath(t), this.ctx.closePath();
            }),
            (A.prototype.formatPath = function (t) {
                var r = this;
                t.forEach(function (n, s) {
                    var B = eA(n) ? n.start : n;
                    s === 0 ? r.ctx.moveTo(B.x, B.y) : r.ctx.lineTo(B.x, B.y),
                        eA(n) &&
                            r.ctx.bezierCurveTo(
                                n.startControl.x,
                                n.startControl.y,
                                n.endControl.x,
                                n.endControl.y,
                                n.end.x,
                                n.end.y
                            );
                });
            }),
            (A.prototype.renderRepeat = function (t, r, n, s) {
                this.path(t),
                    (this.ctx.fillStyle = r),
                    this.ctx.translate(n, s),
                    this.ctx.fill(),
                    this.ctx.translate(-n, -s);
            }),
            (A.prototype.resizeImage = function (t, r, n) {
                var s;
                if (t.width === r && t.height === n) return t;
                var B = (s = this.canvas.ownerDocument) !== null && s !== void 0 ? s : document,
                    i = B.createElement("canvas");
                (i.width = Math.max(1, r)), (i.height = Math.max(1, n));
                var a = i.getContext("2d");
                return a.drawImage(t, 0, 0, t.width, t.height, 0, 0, r, n), i;
            }),
            (A.prototype.renderBackgroundImage = function (t) {
                return J(this, void 0, void 0, function () {
                    var r, n, s, B, i, a;
                    return _(this, function (o) {
                        switch (o.label) {
                            case 0:
                                (r = t.styles.backgroundImage.length - 1),
                                    (n = function (c) {
                                        var l,
                                            g,
                                            w,
                                            M,
                                            W,
                                            Z,
                                            b,
                                            V,
                                            y,
                                            Q,
                                            M,
                                            W,
                                            Z,
                                            b,
                                            V,
                                            f,
                                            H,
                                            d,
                                            F,
                                            L,
                                            v,
                                            p,
                                            h,
                                            m,
                                            y,
                                            E,
                                            M,
                                            Y,
                                            j,
                                            b,
                                            V,
                                            CA,
                                            W,
                                            Z,
                                            LA,
                                            BA,
                                            hA,
                                            KA,
                                            bA,
                                            lA,
                                            xA,
                                            gA;
                                        return _(this, function (GA) {
                                            switch (GA.label) {
                                                case 0:
                                                    if (c.type !== 0) return [3, 5];
                                                    (l = void 0), (g = c.url), (GA.label = 1);
                                                case 1:
                                                    return GA.trys.push([1, 3, , 4]), [4, s.context.cache.match(g)];
                                                case 2:
                                                    return (l = GA.sent()), [3, 4];
                                                case 3:
                                                    return (
                                                        GA.sent(),
                                                        s.context.logger.error("Error loading background-image " + g),
                                                        [3, 4]
                                                    );
                                                case 4:
                                                    return (
                                                        l &&
                                                            ((w = kt(t, r, [l.width, l.height, l.width / l.height])),
                                                            (M = w[0]),
                                                            (W = w[1]),
                                                            (Z = w[2]),
                                                            (b = w[3]),
                                                            (V = w[4]),
                                                            (y = s.ctx.createPattern(s.resizeImage(l, b, V), "repeat")),
                                                            s.renderRepeat(M, y, W, Z)),
                                                        [3, 6]
                                                    );
                                                case 5:
                                                    Wi(c)
                                                        ? ((Q = kt(t, r, [null, null, null])),
                                                          (M = Q[0]),
                                                          (W = Q[1]),
                                                          (Z = Q[2]),
                                                          (b = Q[3]),
                                                          (V = Q[4]),
                                                          (f = Pi(c.angle, b, V)),
                                                          (H = f[0]),
                                                          (d = f[1]),
                                                          (F = f[2]),
                                                          (L = f[3]),
                                                          (v = f[4]),
                                                          (p = document.createElement("canvas")),
                                                          (p.width = b),
                                                          (p.height = V),
                                                          (h = p.getContext("2d")),
                                                          (m = h.createLinearGradient(d, L, F, v)),
                                                          Yr(c.stops, H).forEach(function ($A) {
                                                              return m.addColorStop($A.stop, G($A.color));
                                                          }),
                                                          (h.fillStyle = m),
                                                          h.fillRect(0, 0, b, V),
                                                          b > 0 &&
                                                              V > 0 &&
                                                              ((y = s.ctx.createPattern(p, "repeat")),
                                                              s.renderRepeat(M, y, W, Z)))
                                                        : Zi(c) &&
                                                          ((E = kt(t, r, [null, null, null])),
                                                          (M = E[0]),
                                                          (Y = E[1]),
                                                          (j = E[2]),
                                                          (b = E[3]),
                                                          (V = E[4]),
                                                          (CA = c.position.length === 0 ? [fr] : c.position),
                                                          (W = D(CA[0], b)),
                                                          (Z = D(CA[CA.length - 1], V)),
                                                          (LA = _i(c, W, Z, b, V)),
                                                          (BA = LA[0]),
                                                          (hA = LA[1]),
                                                          BA > 0 &&
                                                              hA > 0 &&
                                                              ((KA = s.ctx.createRadialGradient(
                                                                  Y + W,
                                                                  j + Z,
                                                                  0,
                                                                  Y + W,
                                                                  j + Z,
                                                                  BA
                                                              )),
                                                              Yr(c.stops, BA * 2).forEach(function ($A) {
                                                                  return KA.addColorStop($A.stop, G($A.color));
                                                              }),
                                                              s.path(M),
                                                              (s.ctx.fillStyle = KA),
                                                              BA !== hA
                                                                  ? ((bA = t.bounds.left + 0.5 * t.bounds.width),
                                                                    (lA = t.bounds.top + 0.5 * t.bounds.height),
                                                                    (xA = hA / BA),
                                                                    (gA = 1 / xA),
                                                                    s.ctx.save(),
                                                                    s.ctx.translate(bA, lA),
                                                                    s.ctx.transform(1, 0, 0, xA, 0, 0),
                                                                    s.ctx.translate(-bA, -lA),
                                                                    s.ctx.fillRect(Y, gA * (j - lA) + lA, b, V * gA),
                                                                    s.ctx.restore())
                                                                  : s.ctx.fill())),
                                                        (GA.label = 6);
                                                case 6:
                                                    return r--, [2];
                                            }
                                        });
                                    }),
                                    (s = this),
                                    (B = 0),
                                    (i = t.styles.backgroundImage.slice(0).reverse()),
                                    (o.label = 1);
                            case 1:
                                return B < i.length ? ((a = i[B]), [5, n(a)]) : [3, 4];
                            case 2:
                                o.sent(), (o.label = 3);
                            case 3:
                                return B++, [3, 1];
                            case 4:
                                return [2];
                        }
                    });
                });
            }),
            (A.prototype.renderSolidBorder = function (t, r, n) {
                return J(this, void 0, void 0, function () {
                    return _(this, function (s) {
                        return this.path(vn(n, r)), (this.ctx.fillStyle = G(t)), this.ctx.fill(), [2];
                    });
                });
            }),
            (A.prototype.renderDoubleBorder = function (t, r, n, s) {
                return J(this, void 0, void 0, function () {
                    var B, i;
                    return _(this, function (a) {
                        switch (a.label) {
                            case 0:
                                return r < 3 ? [4, this.renderSolidBorder(t, n, s)] : [3, 2];
                            case 1:
                                return a.sent(), [2];
                            case 2:
                                return (
                                    (B = $c(s, n)),
                                    this.path(B),
                                    (this.ctx.fillStyle = G(t)),
                                    this.ctx.fill(),
                                    (i = Al(s, n)),
                                    this.path(i),
                                    this.ctx.fill(),
                                    [2]
                                );
                        }
                    });
                });
            }),
            (A.prototype.renderNodeBackgroundAndBorders = function (t) {
                return J(this, void 0, void 0, function () {
                    var r,
                        n,
                        s,
                        B,
                        i,
                        a,
                        o,
                        c,
                        l = this;
                    return _(this, function (g) {
                        switch (g.label) {
                            case 0:
                                return (
                                    this.applyEffects(t.getEffects(2)),
                                    (r = t.container.styles),
                                    (n = !mA(r.backgroundColor) || r.backgroundImage.length),
                                    (s = [
                                        { style: r.borderTopStyle, color: r.borderTopColor, width: r.borderTopWidth },
                                        {
                                            style: r.borderRightStyle,
                                            color: r.borderRightColor,
                                            width: r.borderRightWidth,
                                        },
                                        {
                                            style: r.borderBottomStyle,
                                            color: r.borderBottomColor,
                                            width: r.borderBottomWidth,
                                        },
                                        {
                                            style: r.borderLeftStyle,
                                            color: r.borderLeftColor,
                                            width: r.borderLeftWidth,
                                        },
                                    ]),
                                    (B = ll(WA(r.backgroundClip, 0), t.curves)),
                                    n || r.boxShadow.length
                                        ? (this.ctx.save(),
                                          this.path(B),
                                          this.ctx.clip(),
                                          mA(r.backgroundColor) ||
                                              ((this.ctx.fillStyle = G(r.backgroundColor)), this.ctx.fill()),
                                          [4, this.renderBackgroundImage(t.container)])
                                        : [3, 2]
                                );
                            case 1:
                                g.sent(),
                                    this.ctx.restore(),
                                    r.boxShadow
                                        .slice(0)
                                        .reverse()
                                        .forEach(function (w) {
                                            l.ctx.save();
                                            var Q = it(t.curves),
                                                f = w.inset ? 0 : al,
                                                H = jc(
                                                    Q,
                                                    -f + (w.inset ? 1 : -1) * w.spread.number,
                                                    (w.inset ? 1 : -1) * w.spread.number,
                                                    w.spread.number * (w.inset ? -2 : 2),
                                                    w.spread.number * (w.inset ? -2 : 2)
                                                );
                                            w.inset
                                                ? (l.path(Q), l.ctx.clip(), l.mask(H))
                                                : (l.mask(Q), l.ctx.clip(), l.path(H)),
                                                (l.ctx.shadowOffsetX = w.offsetX.number + f),
                                                (l.ctx.shadowOffsetY = w.offsetY.number),
                                                (l.ctx.shadowColor = G(w.color)),
                                                (l.ctx.shadowBlur = w.blur.number),
                                                (l.ctx.fillStyle = w.inset ? G(w.color) : "rgba(0,0,0,1)"),
                                                l.ctx.fill(),
                                                l.ctx.restore();
                                        }),
                                    (g.label = 2);
                            case 2:
                                (i = 0), (a = 0), (o = s), (g.label = 3);
                            case 3:
                                return a < o.length
                                    ? ((c = o[a]),
                                      c.style !== 0 && !mA(c.color) && c.width > 0
                                          ? c.style !== 2
                                              ? [3, 5]
                                              : [4, this.renderDashedDottedBorder(c.color, c.width, i, t.curves, 2)]
                                          : [3, 11])
                                    : [3, 13];
                            case 4:
                                return g.sent(), [3, 11];
                            case 5:
                                return c.style !== 3
                                    ? [3, 7]
                                    : [4, this.renderDashedDottedBorder(c.color, c.width, i, t.curves, 3)];
                            case 6:
                                return g.sent(), [3, 11];
                            case 7:
                                return c.style !== 4
                                    ? [3, 9]
                                    : [4, this.renderDoubleBorder(c.color, c.width, i, t.curves)];
                            case 8:
                                return g.sent(), [3, 11];
                            case 9:
                                return [4, this.renderSolidBorder(c.color, i, t.curves)];
                            case 10:
                                g.sent(), (g.label = 11);
                            case 11:
                                i++, (g.label = 12);
                            case 12:
                                return a++, [3, 3];
                            case 13:
                                return [2];
                        }
                    });
                });
            }),
            (A.prototype.renderDashedDottedBorder = function (t, r, n, s, B) {
                return J(this, void 0, void 0, function () {
                    var i, a, o, c, l, g, w, Q, f, H, d, F, L, v, p, h, p, h;
                    return _(this, function (m) {
                        return (
                            this.ctx.save(),
                            (i = el(s, n)),
                            (a = vn(s, n)),
                            B === 2 && (this.path(a), this.ctx.clip()),
                            eA(a[0]) ? ((o = a[0].start.x), (c = a[0].start.y)) : ((o = a[0].x), (c = a[0].y)),
                            eA(a[1]) ? ((l = a[1].end.x), (g = a[1].end.y)) : ((l = a[1].x), (g = a[1].y)),
                            n === 0 || n === 2 ? (w = Math.abs(o - l)) : (w = Math.abs(c - g)),
                            this.ctx.beginPath(),
                            B === 3 ? this.formatPath(i) : this.formatPath(a.slice(0, 2)),
                            (Q = r < 3 ? r * 3 : r * 2),
                            (f = r < 3 ? r * 2 : r),
                            B === 3 && ((Q = r), (f = r)),
                            (H = !0),
                            w <= Q * 2
                                ? (H = !1)
                                : w <= Q * 2 + f
                                ? ((d = w / (2 * Q + f)), (Q *= d), (f *= d))
                                : ((F = Math.floor((w + f) / (Q + f))),
                                  (L = (w - F * Q) / (F - 1)),
                                  (v = (w - (F + 1) * Q) / F),
                                  (f = v <= 0 || Math.abs(f - L) < Math.abs(f - v) ? L : v)),
                            H && (B === 3 ? this.ctx.setLineDash([0, Q + f]) : this.ctx.setLineDash([Q, f])),
                            B === 3
                                ? ((this.ctx.lineCap = "round"), (this.ctx.lineWidth = r))
                                : (this.ctx.lineWidth = r * 2 + 1.1),
                            (this.ctx.strokeStyle = G(t)),
                            this.ctx.stroke(),
                            this.ctx.setLineDash([]),
                            B === 2 &&
                                (eA(a[0]) &&
                                    ((p = a[3]),
                                    (h = a[0]),
                                    this.ctx.beginPath(),
                                    this.formatPath([new C(p.end.x, p.end.y), new C(h.start.x, h.start.y)]),
                                    this.ctx.stroke()),
                                eA(a[1]) &&
                                    ((p = a[1]),
                                    (h = a[2]),
                                    this.ctx.beginPath(),
                                    this.formatPath([new C(p.end.x, p.end.y), new C(h.start.x, h.start.y)]),
                                    this.ctx.stroke())),
                            this.ctx.restore(),
                            [2]
                        );
                    });
                });
            }),
            (A.prototype.render = function (t) {
                return J(this, void 0, void 0, function () {
                    var r;
                    return _(this, function (n) {
                        switch (n.label) {
                            case 0:
                                return (
                                    this.options.backgroundColor &&
                                        ((this.ctx.fillStyle = G(this.options.backgroundColor)),
                                        this.ctx.fillRect(
                                            this.options.x,
                                            this.options.y,
                                            this.options.width,
                                            this.options.height
                                        )),
                                    (r = zc(t)),
                                    [4, this.renderStack(r)]
                                );
                            case 1:
                                return n.sent(), this.applyEffects([]), [2, this.canvas];
                        }
                    });
                });
            }),
            A
        );
    })(Ss),
    cl = function (e) {
        return e instanceof Cs || e instanceof fs ? !0 : e instanceof Fr && e.type !== nt && e.type !== rt;
    },
    ll = function (e, A) {
        switch (e) {
            case 0:
                return it(A);
            case 2:
                return Jc(A);
            case 1:
            default:
                return at(A);
        }
    },
    gl = function (e) {
        switch (e) {
            case 1:
                return "center";
            case 2:
                return "right";
            case 0:
            default:
                return "left";
        }
    },
    ul = ["-apple-system", "system-ui"],
    Ql = function (e) {
        return /iPhone OS 15_(0|1)/.test(window.navigator.userAgent)
            ? e.filter(function (A) {
                  return ul.indexOf(A) === -1;
              })
            : e;
    },
    wl = (function (e) {
        sA(A, e);
        function A(t, r) {
            var n = e.call(this, t, r) || this;
            return (
                (n.canvas = r.canvas ? r.canvas : document.createElement("canvas")),
                (n.ctx = n.canvas.getContext("2d")),
                (n.options = r),
                (n.canvas.width = Math.floor(r.width * r.scale)),
                (n.canvas.height = Math.floor(r.height * r.scale)),
                (n.canvas.style.width = r.width + "px"),
                (n.canvas.style.height = r.height + "px"),
                n.ctx.scale(n.options.scale, n.options.scale),
                n.ctx.translate(-r.x, -r.y),
                n.context.logger.debug(
                    "EXPERIMENTAL ForeignObject renderer initialized (" +
                        r.width +
                        "x" +
                        r.height +
                        " at " +
                        r.x +
                        "," +
                        r.y +
                        ") with scale " +
                        r.scale
                ),
                n
            );
        }
        return (
            (A.prototype.render = function (t) {
                return J(this, void 0, void 0, function () {
                    var r, n;
                    return _(this, function (s) {
                        switch (s.label) {
                            case 0:
                                return (
                                    (r = sr(
                                        this.options.width * this.options.scale,
                                        this.options.height * this.options.scale,
                                        this.options.scale,
                                        this.options.scale,
                                        t
                                    )),
                                    [4, fl(r)]
                                );
                            case 1:
                                return (
                                    (n = s.sent()),
                                    this.options.backgroundColor &&
                                        ((this.ctx.fillStyle = G(this.options.backgroundColor)),
                                        this.ctx.fillRect(
                                            0,
                                            0,
                                            this.options.width * this.options.scale,
                                            this.options.height * this.options.scale
                                        )),
                                    this.ctx.drawImage(
                                        n,
                                        -this.options.x * this.options.scale,
                                        -this.options.y * this.options.scale
                                    ),
                                    [2, this.canvas]
                                );
                        }
                    });
                });
            }),
            A
        );
    })(Ss),
    fl = function (e) {
        return new Promise(function (A, t) {
            var r = new Image();
            (r.onload = function () {
                A(r);
            }),
                (r.onerror = t),
                (r.src =
                    "data:image/svg+xml;charset=utf-8," + encodeURIComponent(new XMLSerializer().serializeToString(e)));
        });
    },
    Cl = (function () {
        function e(A) {
            var t = A.id,
                r = A.enabled;
            (this.id = t), (this.enabled = r), (this.start = Date.now());
        }
        return (
            (e.prototype.debug = function () {
                for (var A = [], t = 0; t < arguments.length; t++) A[t] = arguments[t];
                this.enabled &&
                    (typeof window != "undefined" && window.console && typeof console.debug == "function"
                        ? console.debug.apply(console, ve([this.id, this.getTime() + "ms"], A))
                        : this.info.apply(this, A));
            }),
            (e.prototype.getTime = function () {
                return Date.now() - this.start;
            }),
            (e.prototype.info = function () {
                for (var A = [], t = 0; t < arguments.length; t++) A[t] = arguments[t];
                this.enabled &&
                    typeof window != "undefined" &&
                    window.console &&
                    typeof console.info == "function" &&
                    console.info.apply(console, ve([this.id, this.getTime() + "ms"], A));
            }),
            (e.prototype.warn = function () {
                for (var A = [], t = 0; t < arguments.length; t++) A[t] = arguments[t];
                this.enabled &&
                    (typeof window != "undefined" && window.console && typeof console.warn == "function"
                        ? console.warn.apply(console, ve([this.id, this.getTime() + "ms"], A))
                        : this.info.apply(this, A));
            }),
            (e.prototype.error = function () {
                for (var A = [], t = 0; t < arguments.length; t++) A[t] = arguments[t];
                this.enabled &&
                    (typeof window != "undefined" && window.console && typeof console.error == "function"
                        ? console.error.apply(console, ve([this.id, this.getTime() + "ms"], A))
                        : this.info.apply(this, A));
            }),
            (e.instances = {}),
            e
        );
    })(),
    hl = (function () {
        function e(A, t) {
            var r;
            (this.windowBounds = t),
                (this.instanceName = "#" + e.instanceCount++),
                (this.logger = new Cl({ id: this.instanceName, enabled: A.logging })),
                (this.cache = (r = A.cache) !== null && r !== void 0 ? r : new Rc(this, A));
        }
        return (e.instanceCount = 1), e;
    })(),
    Ul = function (e, A) {
        return A === void 0 && (A = {}), Fl(e, A);
    };
typeof window != "undefined" && ys.setContext(window);
var Fl = function (e, A) {
        return J(void 0, void 0, void 0, function () {
            var t,
                r,
                n,
                s,
                B,
                i,
                a,
                o,
                c,
                l,
                g,
                w,
                Q,
                f,
                H,
                d,
                F,
                L,
                v,
                p,
                m,
                h,
                m,
                y,
                E,
                M,
                Y,
                j,
                b,
                V,
                CA,
                W,
                Z,
                LA,
                BA,
                hA,
                KA,
                bA,
                lA,
                xA;
            return _(this, function (gA) {
                switch (gA.label) {
                    case 0:
                        if (!e || typeof e != "object")
                            return [2, Promise.reject("Invalid element provided as first argument")];
                        if (((t = e.ownerDocument), !t)) throw new Error("Element is not attached to a Document");
                        if (((r = t.defaultView), !r)) throw new Error("Document is not attached to a Window");
                        return (
                            (n = {
                                allowTaint: (y = A.allowTaint) !== null && y !== void 0 ? y : !1,
                                imageTimeout: (E = A.imageTimeout) !== null && E !== void 0 ? E : 15e3,
                                proxy: A.proxy,
                                useCORS: (M = A.useCORS) !== null && M !== void 0 ? M : !1,
                            }),
                            (s = _t({ logging: (Y = A.logging) !== null && Y !== void 0 ? Y : !0, cache: A.cache }, n)),
                            (B = {
                                windowWidth: (j = A.windowWidth) !== null && j !== void 0 ? j : r.innerWidth,
                                windowHeight: (b = A.windowHeight) !== null && b !== void 0 ? b : r.innerHeight,
                                scrollX: (V = A.scrollX) !== null && V !== void 0 ? V : r.pageXOffset,
                                scrollY: (CA = A.scrollY) !== null && CA !== void 0 ? CA : r.pageYOffset,
                            }),
                            (i = new fA(B.scrollX, B.scrollY, B.windowWidth, B.windowHeight)),
                            (a = new hl(s, i)),
                            (o = (W = A.foreignObjectRendering) !== null && W !== void 0 ? W : !1),
                            (c = {
                                allowTaint: (Z = A.allowTaint) !== null && Z !== void 0 ? Z : !1,
                                onclone: A.onclone,
                                ignoreElements: A.ignoreElements,
                                inlineImages: o,
                                copyStyles: o,
                            }),
                            a.logger.debug(
                                "Starting document clone with size " +
                                    i.width +
                                    "x" +
                                    i.height +
                                    " scrolled to " +
                                    -i.left +
                                    "," +
                                    -i.top
                            ),
                            (l = new pn(a, e, c)),
                            (g = l.clonedReferenceElement),
                            g ? [4, l.toIFrame(t, i)] : [2, Promise.reject("Unable to find element in cloned iframe")]
                        );
                    case 1:
                        return (
                            (w = gA.sent()),
                            (Q = dr(g) || dc(g) ? qs(g.ownerDocument) : lt(a, g)),
                            (f = Q.width),
                            (H = Q.height),
                            (d = Q.left),
                            (F = Q.top),
                            (L = dl(a, g, A.backgroundColor)),
                            (v = {
                                canvas: A.canvas,
                                backgroundColor: L,
                                scale:
                                    (BA = (LA = A.scale) !== null && LA !== void 0 ? LA : r.devicePixelRatio) !==
                                        null && BA !== void 0
                                        ? BA
                                        : 1,
                                x: ((hA = A.x) !== null && hA !== void 0 ? hA : 0) + d,
                                y: ((KA = A.y) !== null && KA !== void 0 ? KA : 0) + F,
                                width: (bA = A.width) !== null && bA !== void 0 ? bA : Math.ceil(f),
                                height: (lA = A.height) !== null && lA !== void 0 ? lA : Math.ceil(H),
                            }),
                            o
                                ? (a.logger.debug("Document cloned, using foreign object rendering"),
                                  (m = new wl(a, v)),
                                  [4, m.render(g)])
                                : [3, 3]
                        );
                    case 2:
                        return (p = gA.sent()), [3, 5];
                    case 3:
                        return (
                            a.logger.debug(
                                "Document cloned, element located at " +
                                    d +
                                    "," +
                                    F +
                                    " with size " +
                                    f +
                                    "x" +
                                    H +
                                    " using computed rendering"
                            ),
                            a.logger.debug("Starting DOM parsing"),
                            (h = Fs(a, g)),
                            L === h.styles.backgroundColor && (h.styles.backgroundColor = wA.TRANSPARENT),
                            a.logger.debug(
                                "Starting renderer for element at " +
                                    v.x +
                                    "," +
                                    v.y +
                                    " with size " +
                                    v.width +
                                    "x" +
                                    v.height
                            ),
                            (m = new ol(a, v)),
                            [4, m.render(h)]
                        );
                    case 4:
                        (p = gA.sent()), (gA.label = 5);
                    case 5:
                        return (
                            (!((xA = A.removeContainer) !== null && xA !== void 0) || xA) &&
                                (pn.destroy(w) ||
                                    a.logger.error("Cannot detach cloned iframe as it is not in the DOM anymore")),
                            a.logger.debug("Finished rendering"),
                            [2, p]
                        );
                }
            });
        });
    },
    dl = function (e, A, t) {
        var r = A.ownerDocument,
            n = r.documentElement ? ue(e, getComputedStyle(r.documentElement).backgroundColor) : wA.TRANSPARENT,
            s = r.body ? ue(e, getComputedStyle(r.body).backgroundColor) : wA.TRANSPARENT,
            B = typeof t == "string" ? ue(e, t) : t === null ? wA.TRANSPARENT : 4294967295;
        return A === r.documentElement ? (mA(n) ? (mA(s) ? B : s) : n) : B;
    };
const pl = ["name", "title", "id", "for", "href", "class"],
    u = { info: console.log, debug: console.debug, error: console.error },
    El = () => new Date().getTime(),
    Hl = (e) => e.nodeType === Node.ELEMENT_NODE,
    We = (e) => ["text", "file", "select"].includes(e),
    gr = (e) => {
        const A = e.tagName.toLowerCase();
        if ((u.debug("[elementClassifier] Classify tag:", A), A === "input")) {
            const t = e;
            switch ((u.debug("[elementClassifier] Element from input:", t), t.type)) {
                case "password":
                    return { type: "text", value: t.value };
                case "radio":
                    return { type: "radio", value: t.value };
                case "checkbox":
                    return { type: "checkbox", value: t.checked };
                case "file":
                    return { type: "file", value: t.value };
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
                    return { type: "text", value: t.value };
                case "submit":
                case "image":
                case "range":
                case "reset":
                    return { type: t.type, value: void 0 };
            }
        } else if (A === "textarea") {
            const t = e;
            return u.debug("[elementClassifier] Element from textarea:", t), { type: "text", value: t.value };
        } else if (A === "select") {
            const t = e;
            return u.debug("[elementClassifier] Element from select:", t), { type: "select", value: t.value };
        } else if (A === "a") {
            const t = e;
            return u.debug("[classifyRawElement] Element from a:", t), { type: "a", value: t.href };
        } else if (A === "button") {
            const t = e;
            return u.debug("[elementClassifier] Element from button:", t), { type: "button", value: t.value };
        } else if (typeof e.onclick == "function" || typeof e.onmousedown == "function") {
            u.debug("[elementClassifier] Element from unknown element with onClick function:", e); //! TODO: This might need replacement with a better object
            return { type: "reset", value: void 0 };
        }
        u.debug("[elementClassifier] ERROR - Element could not be classified");
    },
    vl = {
        parseNode(e, A, t, r) {
            if (
                (u.debug("Parsing Node:", e, "selectors:", A, "attributesArray:", t, "forceClassified:", r),
                e !== void 0)
            ) {
                u.debug("[scanner.parseNode] Creating hash...");
                let n = r || gr(e);
                n === void 0 && e.parentElement && ((n = gr(e.parentElement)), (e = e.parentElement)),
                    u.debug("[scanner.parseNode] Hash:", n);
                const s = Il.build(e, t, []);
                u.debug("[scanner.parseNode] Tree:", s);
                const B = El();
                if (n !== void 0) {
                    const i = ml.build(s, e, n.type || "default");
                    u.debug("[scanner.parseNode] Built path:", i);
                    const a = Ae(DA({}, n), { selectors: A, time: B, path: i });
                    return u.debug("[scanner.parseNode] Parsed Node:", a), a;
                }
                u.error("[scanner.parseNode] Parsing failed. No Hash!");
                return;
            }
            u.error("[scanner.parseNode] Parsing failed. No Node!");
        },
    },
    $e = (e, A, t) => {
        try {
            u.debug("[classifyEvent] Classifying event:", e);
            const r = e.target;
            if (!(r instanceof HTMLElement || r instanceof SVGElement)) {
                u.debug("Element not HTMLElement:", r);
                return;
            }
            const n = A.buildStrategies(r).map((B) => A.getSelectorAsObject(B));
            if ((u.debug("[classifyEvent] Selectors (mapped) from builder:", n), n.length === 0)) {
                u.debug("[classifyEvent] Skipping committing due to no selectors");
                return;
            }
            const s = vl.parseNode(r, n, pl, t);
            if ((u.debug("[classifyEvent] Element attributes:", s), !s)) {
                u.debug("[classifyEvent] Skipping committing due to no relevant attributes");
                return;
            }
            return s.type === "text" && s.value === ""
                ? (u.debug("[classifyEvent] Skipping saving empty text event"),
                  { selectors: [], node: void 0, skipError: !0 })
                : { selectors: n, node: s };
        } catch (r) {
            u.error("[classifyEvent] Could not classify event due to error:", r);
            return;
        }
    },
    Il = {
        _getIndex(e) {
            let A = !1,
                t = 0,
                r = 0;
            if (!e.parentNode) return 0;
            const n = e.parentNode.childNodes;
            for (let s = 0; s < n.length; s++) {
                n[s] === e && (A = !0);
                const B = n[s];
                Hl(B) && B.tagName === e.tagName && ((t += 1), (r = A ? r : r + 1));
            }
            return t > 1 ? r + 1 : 0;
        },
        _buildAttributes(e, A) {
            return A.map((r) => {
                let n;
                return (
                    r === "className"
                        ? (n = e.className.length > 0 ? e.className.split(" ") : null)
                        : r === "index"
                        ? (n = 1)
                        : (n = e.getAttribute(r)),
                    n ? { [`${r}`]: n } : null
                );
            }).filter((r) => r);
        },
        build(e, A, t) {
            if (
                (u.debug("[builder.build] Building for element:", e, "with attributes:", A, "and pathList:", t),
                !e || !e.parentNode || e.nodeType === Node.DOCUMENT_NODE)
            )
                return t;
            const r = this._buildAttributes(e, A);
            return t.push({ [`${e.tagName.toLowerCase()}`]: r }), this.build(e.parentNode, A, t);
        },
    },
    ml = {
        build(e, A, t) {
            const r = e[0],
                n = Object.keys(r)[0],
                s = r[n].reduce((o, c) => (o === "" ? this._getSubpath(o, c, n) : o), ""),
                B = `/${s}`;
            if (
                (u.debug("[locator.build] Building for Item:", r, "tag:", n, "p:", s, "path:", B),
                !A ||
                    this._found(["@id", "@for"], B) ||
                    (this._found(["@name"], B) && this._found(["select"], t)) ||
                    B === "/")
            )
                return B;
            const { count: i, index: a } = this._getIndex(B, A);
            return i > 1 && a > 1 ? `xpath=(${B})[${a}]` : B;
        },
        _found(e, A) {
            return e.some((t) => A.includes(t));
        },
        _getIndex(e, A) {
            let t = 1,
                r = 1,
                n;
            const s = document.evaluate(`.${e}`, document.body, null, XPathResult.ORDERED_NODE_ITERATOR_TYPE, null);
            for (; n === s.iterateNext(); ) n === A && (t = r), (r += 1);
            return { count: r, index: t };
        },
        _getSubpath(e, A, t) {
            return A.for != null
                ? `/${t}[@for="${A.for}"]`
                : A.class != null && typeof A.class != "number" && A.class.length > 0
                ? `/${t}[@class="${A.class}"]`
                : A.title != null
                ? `/${t}[@title="${A.title}"]`
                : A.href != null
                ? `/${t}[@href="${A.href}"]`
                : A.name != null
                ? `/${t}[@name="${A.name}"]`
                : A.id != null
                ? `/${t}[@id="${A.id}"]`
                : A.index != null
                ? `/${t}`
                : "";
        },
    };
var Ts = ((e) => ((e.Browser = "browser"), (e.Windows = "windows"), (e.Image = "image"), e))(Ts || {});
const TA = {
    isElement: (e) => e.nodeType === window.Node.ELEMENT_NODE,
    isImage: (e) => e.nodeName.toUpperCase() === "IMG",
    isLink: (e) => e.nodeName.toUpperCase() === "A",
    isInput: (e) => e.nodeName.toUpperCase() === "INPUT",
    isLabel: (e) => e.nodeName.toUpperCase() === "LABEL",
};
class yl {
    constructor(A) {
        (this.buildLocator = (t) =>
            UA(this, null, function* () {
                u.debug("[builder] Building locator for Element:", t), u.debug("[builder] Building source...");
                const r = `${this.window.location.protocol}//${this.window.location.host}/${this.window.location.pathname}${this.window.location.search}`;
                u.debug("[builder] Building element tag...");
                const n = t.tagName;
                u.debug("[builder] Building element type & value...");
                const s = gr(t);
                u.debug("[builder] Building alternatives...");
                const B = this.buildStrategies(t).map(([c, l]) => ({ strategy: c, value: l, matches: 1 }));
                u.debug("[builder] Building screenshot...");
                const a = (yield Ul(t)).toDataURL("image/png"),
                    o = {
                        type: Ts.Browser,
                        source: r,
                        strategy: B[0].strategy,
                        value: B[0].value,
                        element: { tag: n, type: s == null ? void 0 : s.type, modifier: s == null ? void 0 : s.value },
                        alternatives: B,
                        screenshot: a,
                    };
                return u.debug("[builder] Returning locator:", o), o;
            })),
            (this.buildStrategies = (t) => {
                u.debug("[builder] Building strategies for Element:", t);
                const r = [
                        ["id", this.buildId],
                        ["link", this.buildLinkText],
                        ["name", this.buildName],
                        ["css", this.buildCssFinder],
                        ["css:attributes", this.buildCssDataAttr],
                        ["xpath:link-text", this.buildXPathLink],
                        ["xpath:image", this.buildXPathImg],
                        ["xpath:attributes", this.buildXPathAttr],
                        ["xpath:relative-id", this.buildXPathIdRelative],
                        ["xpath:href", this.buildXPathHref],
                        ["xpath:position", this.buildXPathPosition],
                        ["xpath:inner-text", this.buildXPathInnerText],
                        ["xpath:input-label", this.buildXPathInputLabel],
                    ],
                    n = [];
                return (
                    r.forEach(([s, B]) => {
                        try {
                            const i = B(t);
                            i && (typeof i == "string" ? n.push([s, i]) : i.forEach((a) => n.push([s, a])));
                        } catch (i) {
                            u.error(`[builder] Failed to build '${s}': ${i}`);
                        }
                    }),
                    n
                );
            }),
            (this.logValidation = (t, r) => (
                t
                    ? u.debug("[builder] Selector validation PASSED for:", r)
                    : u.debug("[builder] Selector validation FAILED for:", r),
                t
            )),
            (this.validateId = (t) => document.getElementById(t) !== null),
            (this.validateName = (t) => document.getElementsByName(t) !== null),
            (this.validateXPath = (t) => document.evaluate(t, document, null, XPathResult.ANY_TYPE, null) !== null),
            (this.validateCSS = (t) => document.querySelector(t) !== null),
            (this.getSelectorAsObject = (t) => ({ strategy: t[0].split(":", 1)[0], value: t[1] })),
            (this.getElementByXPath = (t) =>
                document.evaluate(t, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue),
            (this.getXPathFromParent = (t) => {
                let r = "/" + t.nodeName.toLowerCase();
                const n = this.getNodeNumber(t);
                return n > 0 && (r += "[" + (n + 1) + "]"), r;
            }),
            (this.getNodeNumber = (t) => {
                var s;
                const r = ((s = t.parentNode) == null ? void 0 : s.childNodes) || [];
                let n = 0;
                for (let B = 0; B < r.length; B++) {
                    const i = r[B];
                    if (i.nodeName === t.nodeName) {
                        if (i === t) return n;
                        n++;
                    }
                }
                return 0;
            }),
            (this.getUniqueXPath = (t, r) => {
                if (r !== this.getElementByXPath(t)) {
                    const n = r.ownerDocument.evaluate(
                        t,
                        r.ownerDocument,
                        null,
                        XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
                        null
                    );
                    for (let s = 0, B = n.snapshotLength; s < B; s++) {
                        const i = "(" + t + ")[" + (s + 1) + "]";
                        if (r === this.getElementByXPath(i)) return i;
                    }
                }
                return t;
            }),
            (this.getXPathValue = (t) => {
                if (t.indexOf("'") < 0) return "'" + t + "'";
                if (t.indexOf('"') < 0) return '"' + t + '"';
                {
                    let r = "concat(",
                        n = "",
                        s = !1;
                    for (; !s; ) {
                        const B = t.indexOf("'"),
                            i = t.indexOf('"');
                        if (B < 0) {
                            (r += "'" + t + "'"), (s = !0);
                            break;
                        } else if (i < 0) {
                            (r += '"' + t + '"'), (s = !0);
                            break;
                        } else
                            i < B
                                ? ((n = t.substring(0, B)), (r += "'" + n + "'"), (t = t.substring(n.length)))
                                : ((n = t.substring(0, i)), (r += '"' + n + '"'), (t = t.substring(n.length)));
                        r += ",";
                    }
                    return (r += ")"), r;
                }
            }),
            (this.buildCssDataAttr = (t) => {
                const r = ["data-test", "data-test-id"];
                for (let n = 0; n < r.length; n++) {
                    const s = r[n],
                        B = t.getAttribute(s);
                    if (B) return "css=*[" + s + '="' + B + '"]';
                }
                return null;
            }),
            (this.buildId = (t) =>
                t.hasAttribute("id") && this.logValidation(this.validateId(t.id), "id:" + t.id) ? t.id : null),
            (this.buildLinkText = (t) => {
                if (!TA.isLink(t)) return null;
                const r = t.textContent || "";
                return r.match(/^\s*$/) ? null : r.replace(/\xA0/g, " ").replace(/^\s*(.*?)\s*$/, "$1");
            }),
            (this.buildName = (t) => {
                if (t.hasAttribute("name")) {
                    const r = t.getAttribute("name");
                    if (r && this.logValidation(this.validateName(r), "name:" + r)) return r;
                }
                return null;
            }),
            (this.buildCssFinder = (t) => {
                const r = Vs(t);
                return r && this.logValidation(this.validateCSS(r), "css:" + r) ? r : null;
            }),
            (this.buildXPathLink = (t) => {
                if (!TA.isLink(t)) return null;
                const r = t.textContent || "";
                if (r.match(/^\s*$/)) return null;
                const s = "//a[contains(text(),'" + r.replace(/^\s+/, "").replace(/\s+$/, "") + "')]",
                    B = this.getUniqueXPath(s, t);
                return B && this.logValidation(this.validateXPath(B), "xpath:" + B) ? B : null;
            }),
            (this.buildXPathImg = (t) => {
                if (!TA.isImage(t)) return null;
                let r = "";
                if (t.alt) r = "//img[@alt=" + this.getXPathValue(t.alt) + "]";
                else if (t.title) r = "//img[@title=" + this.getXPathValue(t.title) + "]";
                else if (t.src) r = "//img[contains(@src," + this.getXPathValue(t.src) + ")]";
                else return null;
                const n = this.getUniqueXPath(r, t);
                return n && this.logValidation(this.validateXPath(n), "xpath:" + n) ? n : null;
            }),
            (this.buildXPathAttr = (t) => {
                const r = ["id", "name", "value", "type", "action", "onclick"],
                    n = (a, o, c) => {
                        let l = "//" + a + "[";
                        for (let g = 0; g < o.length; g++) {
                            g > 0 && (l += " and ");
                            const w = o[g],
                                Q = this.getXPathValue(c[w]);
                            l += "@" + w + "=" + Q;
                        }
                        return (l += "]"), this.getUniqueXPath(l, t);
                    };
                if (!t.attributes) return null;
                const s = {},
                    B = t.attributes;
                for (let a = 0; a < B.length; a++) {
                    const o = B[a];
                    s[o.name] = o.value;
                }
                const i = [];
                for (let a = 0; a < r.length; a++) {
                    const o = r[a];
                    if (!s[o]) continue;
                    i.push(o);
                    const c = n(t.nodeName.toLowerCase(), i, s);
                    if (t === this.getElementByXPath(c) && c && this.logValidation(this.validateXPath(c), "xpath:" + c))
                        return c;
                }
                return null;
            }),
            (this.buildXPathIdRelative = (t) => {
                let r = "",
                    n = t;
                for (; n; ) {
                    const s = n.parentNode;
                    if (!s) return null;
                    if (((r = this.getXPathFromParent(n) + r), TA.isElement(s) && s.getAttribute("id"))) {
                        const B = s.nodeName.toLowerCase(),
                            i = this.getXPathValue(s.getAttribute("id") || ""),
                            a = "//" + B + "[@id=" + i + "]" + r,
                            o = this.getUniqueXPath(a, t);
                        if (o && this.logValidation(this.validateXPath(o), "xpath:" + o)) return o;
                    }
                    n = s;
                }
                return null;
            }),
            (this.buildXPathHref = (t) => {
                if (!t.hasAttribute("href")) return null;
                const r = t.getAttribute("href") || "";
                if (!r) return null;
                let n;
                r.search(/^http?:\/\//) >= 0
                    ? (n = "//a[@href=" + this.getXPathValue(r) + "]")
                    : (n = "//a[contains(@href, " + this.getXPathValue(r) + ")]");
                const s = this.getUniqueXPath(n, t);
                return s && this.logValidation(this.validateXPath(s), "xpath:" + s) ? s : null;
            }),
            (this.buildXPathPosition = (t) => {
                let r = "",
                    n = t;
                for (; n; ) {
                    const s = n.parentNode;
                    s ? (r = this.getXPathFromParent(n) + r) : (r = "/" + n.nodeName.toLowerCase() + r);
                    const B = "/" + r;
                    if (t === this.getElementByXPath(B) && B && this.logValidation(this.validateXPath(B), "xpath:" + B))
                        return B;
                    n = s;
                }
                return null;
            }),
            (this.buildXPathInnerText = (t) => {
                if (!(t instanceof HTMLElement) || !t.innerText) return null;
                const r = t.nodeName.toLowerCase(),
                    n = this.getXPathValue(t.innerText),
                    s = "//" + r + "[contains(.," + n + ")]",
                    B = this.getUniqueXPath(s, t);
                return B && this.logValidation(this.validateXPath(B), "xpath:" + B) ? s : null;
            }),
            (this.buildXPathInputLabel = (t) => {
                if (!TA.isInput(t)) return null;
                const r = document.getElementsByTagName("LABEL"),
                    n = {};
                for (let o = 0; o < r.length; o++) {
                    const c = r[o];
                    TA.isLabel(c) && c.htmlFor && document.getElementById(c.htmlFor) && (n[c.htmlFor] = c);
                }
                let s;
                if (t.id && Object.prototype.hasOwnProperty.call(t, "id")) s = n[t.id];
                else {
                    const o = t.parentNode;
                    if (!o) return null;
                    const c = [],
                        l = o.childNodes;
                    for (let g = 0; g < l.length; g++) {
                        const w = l[g];
                        TA.isLabel(w) && c.push(w);
                    }
                    if (c.length !== 1) return null;
                    s = c[0];
                }
                const i = "//label[contains(.," + this.getXPathValue(s.innerText) + ")]/../input",
                    a = this.getUniqueXPath(i, t);
                return a && this.logValidation(this.validateXPath(a), "xpath:" + a) ? a : null;
            }),
            (this.window = A);
    }
}
const ur = (e) =>
        new Promise((A) => {
            setTimeout(A, e);
        }),
    $ = {
        getFrameDiv() {
            const e = document.getElementById("inspector-frame") || document.createElement("div");
            return (e.id = "inspector-frame"), e;
        },
        focusElement(e) {
            u.debug("[frame] Focusing on element:", e),
                e.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
            const A = document.createElement("div"),
                t = document.documentElement.getBoundingClientRect(),
                r = e.getBoundingClientRect();
            (A.id = "inspector-focus"),
                (A.style.left = `${r.left - t.left}px`),
                (A.style.top = `${r.top - t.top}px`),
                (A.style.width = `${r.width}px`),
                (A.style.height = `${r.height}px`),
                document.body.appendChild(A),
                setTimeout(() => {
                    document.body.removeChild(A);
                }, 500);
        },
        recorderSetErrorState() {
            u.debug("[frame.recorder] Settingstate to: error");
            const e = this.getFrameDiv();
            (e.className = "error"),
                setTimeout(() => {
                    u.debug("[frame.recorder] Resetting error state"), (e.className = "recorder");
                }, 1250);
        },
        pickerSetPauseState(e) {
            if ((u.debug("[frame.picker] Setting state to: paused"), e)) {
                const A = this.getFrameDiv();
                A.className = "paused";
            } else {
                const A = this.getFrameDiv();
                A.className = "picker";
            }
        },
        pickerSetSavingState(e) {
            if ((u.debug("[frame.picker] Setting state to: in_progress"), e)) {
                const A = this.getFrameDiv();
                A.className = "picker_in_progress";
            } else {
                const A = this.getFrameDiv();
                A.className = "picker";
            }
        },
    };
class Ll {
    constructor(A, t, r) {
        (this.isPaused = !1),
            (this.setApp = (n) => {
                this.app = n;
            }),
            (this.setOnPick = (n) => {
                this.onPick = n;
            }),
            (this.setBuilder = (n) => {
                this.builder = n;
            }),
            (this.setNonStopRun = (n) => {
                this.nonStopRun = n;
            }),
            (this.addInfoBox = () => {
                const n = document.createElement("div");
                (n.id = "inspector-info-box"), (this.infoBox = n), document.body.appendChild(this.infoBox);
            }),
            (this._showPick = (n, s) => {
                const B = n.target;
                B !== s &&
                    (this._removeHighlights(),
                    B instanceof Element &&
                        (this.app === "recorder"
                            ? $e(n, this.builder, { type: "verify", value: void 0 }) && this._addHighlight(B)
                            : this._addHighlight(B),
                        (s = B)));
            }),
            (this._showDivInfo = (n) => {
                n.target instanceof HTMLElement &&
                    this.infoBox &&
                    this.builder &&
                    ((this.infoBox.textContent = "No element to target"),
                    (this.infoBox.style.left = `${n.pageX - 8}px`),
                    (this.infoBox.style.top = `${n.pageY - 20}px`));
            }),
            (this._addHighlight = (n) => {
                u.debug("[picker] Adding highlight to: ", n), n.setAttribute("data-inspector-highlight", "");
            }),
            (this._removeHighlights = () => {
                u.debug("[picker] Removing highlight...");
                const n = document.querySelectorAll("[data-inspector-highlight]");
                for (let s = 0; s < n.length; s++) n[s].removeAttribute("data-inspector-highlight");
            }),
            (this._pickElement = (n) =>
                UA(this, null, function* () {
                    var B;
                    u.debug("[picker] Picking Element:", n), n.preventDefault(), n.stopPropagation();
                    const s = n.target;
                    if (s instanceof HTMLElement || s instanceof SVGElement) {
                        $.pickerSetSavingState(!0);
                        try {
                            this._removeHighlights();
                            const i = yield (B = this.builder) == null ? void 0 : B.buildLocator(s);
                            u.debug("[picker] Built locator:", i),
                                typeof this.onPick == "function"
                                    ? (u.debug("[picker] Calling callback:", this.onPick), this.onPick(i))
                                    : u.error("[picker] The onPick function is not set");
                        } catch (i) {
                            u.error(i);
                        } finally {
                            setTimeout(() => {
                                $.pickerSetSavingState();
                            }, 1500),
                                this.nonStopRun || this._removeAll();
                        }
                    }
                })),
            (this._checkCombination = (n) => {
                u.debug("[picker] Canceling Pick:", n);
                const s = n || window.event;
                !!s.shiftKey &&
                    ((s.key === "Escape" || s.keyCode === 27) && !this.isPaused
                        ? (u.debug("[picker] Pausing callbacks..."),
                          document.removeEventListener("mousemove", this._showPick, !0),
                          document.removeEventListener("click", this._pickElement, !0),
                          this._removeHighlights(),
                          u.debug("[picker] Pausing picker..."),
                          $.pickerSetPauseState(!0),
                          (this.isPaused = !0))
                        : (s.key === "Escape" || s.keyCode === 27) &&
                          (u.debug("[picker] Unpausing picker..."),
                          $.pickerSetPauseState(!1),
                          u.debug("[picker] Unpausing callbacks..."),
                          document.addEventListener("mousemove", this._showPick, !0),
                          document.addEventListener("click", this._pickElement, !0),
                          (this.isPaused = !1)));
            }),
            (this._removeAll = () => {
                u.debug("[picker] Removing all...");
                const n = document.getElementById("inspector-frame");
                n && document.body.removeChild(n);
                const s = document.getElementById("inspector-info-box");
                s && document.body.removeChild(s),
                    document.removeEventListener("mousemove", this._showPick, !0),
                    document.removeEventListener("click", this._pickElement, !0),
                    document.removeEventListener("keydown", this._checkCombination, !0),
                    this._removeHighlights();
            }),
            (this.builder = A),
            (this.app = t || "picker"),
            (this.nonStopRun = r);
    }
}
const mn = 750,
    Kl = () => {
        let e = !1;
        return {
            isLocked: e,
            acquire: () =>
                UA(exports, null, function* () {
                    u.debug("Acquiring lock...");
                    let r = !1;
                    for (
                        let n = 0;
                        n < 200 &&
                        (yield ur(10).then(() => {
                            e === !0 && (r = !0);
                        }),
                        !r);
                        n++
                    );
                    if (!r) throw Error("Timeout while acquiring lock");
                    e = !0;
                }),
            release: () =>
                UA(exports, null, function* () {
                    u.debug("Releasing lock..."), (e = !1);
                }),
        };
    };
class bl {
    constructor(A, t) {
        (this.recordEvent = (n) => {
            this._removeListeners(), (this.actionsList = []);
            let s = document.getElementById("inspector-frame");
            !this.lock.isLocked &&
                !s &&
                ((s = document.createElement("div")),
                (s.id = "inspector-frame"),
                (s.className = "recorder"),
                document.body.appendChild(s)),
                (this.callback = n),
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
            (this._handleInputChange = (n) => {
                u.debug("[recorder] Input Change Event:", n), (this.inputEvent = n);
            }),
            (this._handleContextMenu = (n) => {
                const s = n.target;
                if (s instanceof HTMLElement || s instanceof SVGElement)
                    try {
                        n.preventDefault();
                        const B = $e(n, this.builder, { type: "verify", value: void 0 });
                        if (B === void 0 || B.node === void 0) {
                            (B != null && B.skipError) || $.recorderSetErrorState();
                            return;
                        }
                        const i = Ae(DA({}, B.node), { trigger: "click" });
                        u.debug("[recorder] Appending wait action:", i),
                            this.actionsList.push(i),
                            u.debug("[recorder] Event list:", this.actionsList),
                            $.focusElement(s),
                            u.debug("[recorder] Passing click event through callback -> WAITING..."),
                            this._sendEvents();
                    } catch (B) {
                        u.debug("[recorder] Skipping committing wait due to error", B), $.recorderSetErrorState();
                    }
            }),
            (this._handleChange = (n) => {
                u.debug("[recorder] Change Event:", n);
                const s = n.target;
                if (!(s instanceof HTMLElement || s instanceof SVGElement)) return;
                const B = $e(n, this.builder);
                if (B === void 0 || B.node === void 0) {
                    (B != null && B.skipError) || $.recorderSetErrorState();
                    return;
                }
                u.debug("[recorder] Is recording in progress:", this.lock.isLocked), this.lock.acquire();
                try {
                    if ((u.debug("[recorder] Is handled by change?:", We(B.node.type)), We(B.node.type))) {
                        const i = $.getFrameDiv();
                        (i.className = "recorder_in_progress"),
                            u.debug("[recorder] Preventing propagation..."),
                            n.preventDefault(),
                            n.stopPropagation();
                        const a = Ae(DA({}, B.node), { trigger: "change" });
                        u.debug("[recorder] Appending change action", a),
                            this.actionsList.push(a),
                            u.debug("[recorder] Event list:", this.actionsList),
                            u.debug("[recorder] Passing change event through callback"),
                            this._sendEvents(),
                            (() =>
                                UA(this, null, function* () {
                                    return yield ur(mn).then(() => {
                                        (i.className = "recorder"), this.lock.release();
                                    });
                                }))();
                    } else u.debug("[recorder] Skipping committing change - will be handled by onClick handler");
                } catch (i) {
                    u.debug("[recorder] Skipping committing change due to error", i), $.recorderSetErrorState();
                }
                (this.inputEvent = void 0), this.lock.release();
            }),
            (this._handleClick = (n) =>
                UA(this, null, function* () {
                    u.info("[recorder] Click Event:", n);
                    const s = n.target;
                    if (
                        (this.inputEvent && !this.lock.isLocked && this._handleChange(this.inputEvent),
                        !(s instanceof HTMLElement || s instanceof SVGElement))
                    )
                        return;
                    if (n.detail === -1) {
                        u.debug("[recorder] Dummy click. Exiting...");
                        return;
                    }
                    const B = $e(n, this.builder);
                    if (B === void 0 || B.node === void 0) {
                        (B != null && B.skipError) || $.recorderSetErrorState();
                        return;
                    }
                    u.debug("[recorder] Is recording in progress:", this.lock.isLocked), this.lock.acquire();
                    try {
                        if ((u.debug("[recorder] Is handled by change?:", We(B.node.type)), We(B.node.type)))
                            u.debug("[recorder] Skipping committing click - will be handled by onChange handler"),
                                this.lock.release();
                        else {
                            const i = document.getElementById("inspector-frame") || document.createElement("div");
                            (i.className = "recorder_in_progress"),
                                u.debug("[recorder] Preventing propagation..."),
                                n.preventDefault(),
                                n.stopPropagation();
                            const a = Ae(DA({}, B.node), { trigger: "click" });
                            u.debug("[recorder] Appending click action:", a),
                                this.actionsList.push(a),
                                u.debug("[recorder] Event list:", this.actionsList),
                                u.debug("[recorder] Passing click event through callback -> RECORDING..."),
                                this._sendEvents(),
                                (() =>
                                    UA(this, null, function* () {
                                        return yield ur(mn).then(() => {
                                            u.debug("[recorder] Pushing dummy event..."),
                                                (i.className = "recorder"),
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
                    } catch (i) {
                        u.debug("[recorder] Skipping committing click due to error", i), $.recorderSetErrorState();
                    }
                })),
            (this._handleKeyboardEvent = (n) => {
                const s = n || window.event;
                (s.key === "Escape" || s.keyCode === 27) && this.stop(),
                    (s.key === "Tab" || s.keyCode === 9) && this.inputEvent && this._handleChange(this.inputEvent);
            }),
            (this._sendEvents = (n) => {
                this.callback
                    ? (this.callback({ actionType: "event", actions: this.actionsList, url: document.URL }),
                      u.debug("[recorder] Successfully invoked callback:", {
                          actionType: "event",
                          action: this.actionsList,
                          url: document.URL,
                      }),
                      n && (this.actionsList = []))
                    : u.debug("[recorder] No callback function defined");
            }),
            (this.builder = A),
            (this.picker = t),
            this.picker.setApp("recorder"),
            (this.actionsList = []),
            (this.lock = Kl()),
            (this.inputEvent = void 0);
        const r = document.getElementById("inspector-style") || document.createElement("style");
        (r.id = "inspector-style"), (r.type = "text/css"), document.head.appendChild(r);
    }
}
class xl {
    constructor() {
        (this.startPicker = (t, r) => {
            u.debug("[inspector] Starting picker..."),
                (this.onPickCallback = t),
                u.debug("[inspector] Will User Pick Non-Stop?", r),
                (this.nonStopRun = r),
                this.picker.setNonStopRun(r),
                this.picker.setOnPick(this.onPickCallback),
                this.picker._removeHighlights();
            const n = document.getElementById("inspector-frame") || document.createElement("div");
            (n.id = "inspector-frame"),
                (n.className = "picker"),
                document.body.appendChild(n),
                document.addEventListener("mousemove", this.picker._showPick, !0),
                document.addEventListener("click", this.picker._pickElement, !0),
                document.addEventListener("keydown", this.picker._checkCombination, !0);
        }),
            (this.highlightElements = (t) => {
                u.debug("[inspector] Highlighting elements:", t);
                for (let r = 0; r < t.length; r++) this.picker._addHighlight(t[r]);
            }),
            (this.describeElements = (t) => {
                u.debug("[inspector] Describing elements:", t);
                const r = [];
                for (let n = 0; n < t.length; n++) {
                    const s = t[n].cloneNode(!1).outerHTML;
                    r.push(s);
                }
                return r;
            }),
            (this.removeHighlights = () => {
                u.debug("[inspector] Removing highlights"), this.picker._removeHighlights();
            }),
            (this.cancelPick = () => {
                u.debug("[inspector] Cancelling pick and removing highlights"), this.picker._removeAll();
            }),
            (this.focusElement = (t) => $.focusElement(t)),
            (this.recordEvent = (t) => (u.debug("[inspector] Recording event..."), this.recorder.recordEvent(t))),
            (this.stopRecording = () => {
                u.debug("[inspector] Stopping recording..."), (window.InspectorStop = !0), this.recorder.stop();
            }),
            (this.builder = new yl(window)),
            (this.picker = new Ll(this.builder)),
            (this.recorder = new bl(this.builder, this.picker)),
            (this.nonStopRun = !1),
            (this.currentPick = void 0),
            (this.onPickCallback = void 0);
        const A = document.getElementById("inspector-style") || document.createElement("style");
        (A.id = "inspector-style"), (A.type = "text/css"), document.head.appendChild(A);
    }
}
window.Inspector = new xl();
