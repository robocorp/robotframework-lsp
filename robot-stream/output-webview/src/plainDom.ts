function byId<type>(id: string): type {
    return <type>document.getElementById(id);
}

export function divById(id: string): HTMLDivElement {
    return byId<HTMLDivElement>(id);
}

export function selectById(id: string): HTMLSelectElement {
    return byId<HTMLSelectElement>(id);
}

export function createUL(id: string): HTMLUListElement {
    const element = document.createElement("ul");
    element.setAttribute("data-tree-id", id);
    return element;
}

export function createSummary(): HTMLElement {
    return document.createElement("summary");
}

export function createSpan(): HTMLSpanElement {
    return document.createElement("span");
}

export function createLI(id: string): HTMLLIElement {
    const element = document.createElement("li");
    element.setAttribute("data-tree-id", id);
    return element;
}

export function createDetails(): HTMLDetailsElement {
    return document.createElement("details");
}

export function getDataTreeId(element: HTMLLIElement | HTMLUListElement) {
    return element.getAttribute("data-tree-id");
}
