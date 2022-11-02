import { IOpts } from "./protocols";
import { getState } from "./vscodeComm";

let _opts: IOpts = {
    outputFileContents: undefined,
    runId: undefined,
    state: undefined,
    onClickReference: undefined,
};

export function getOpts(): IOpts {
    if (_opts.state === undefined) {
        _opts.state = getState();
    }
    return _opts;
}
