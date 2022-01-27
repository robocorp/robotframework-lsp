export function jsonEscapeUTF(str: string) {
    let result = "";
    for (let i = 0; i < str.length; i++) {
        let ch = str.charCodeAt(i);

        if (ch < 128) {
            // i.e.: escape any char which isn't ascii.
            result += str.charAt(i);
        } else {
            result += "\\u" + ("000" + ch.toString(16)).slice(-4);
        }
    }
    return result;
}
