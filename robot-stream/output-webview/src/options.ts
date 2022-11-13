import { IOpts } from "./protocols";
import { getState } from "./vscodeComm";

let _opts: IOpts = {
    initialContents: undefined,
    runId: undefined,
    state: undefined,
    label: "",
    onClickReference: undefined,
    appendedContents: [],
};

export function getOpts(): IOpts {
    if (_opts.state === undefined) {
        _opts.state = getState();
    }
    return _opts;
}
