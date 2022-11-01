function byId<type>(id: string): type {
    return <type>document.getElementById(id);
}

export function divById(id: string): HTMLDivElement {
    return byId<HTMLDivElement>(id);
}

export function selectById(id: string): HTMLSelectElement {
    return byId<HTMLSelectElement>(id);
}

export function createUL(): HTMLUListElement {
    return document.createElement("ul");
}

export function createSummary(): HTMLElement {
    return document.createElement("summary");
}

export function createSpan(): HTMLSpanElement {
    return document.createElement("span");
}

export function createLI(): HTMLLIElement {
    return document.createElement("li");
}

export function createDetails(): HTMLDetailsElement {
    return document.createElement("details");
}
