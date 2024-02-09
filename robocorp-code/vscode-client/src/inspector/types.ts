/**
 * @source https://github.com/robocorp/inspector-ext/blob/master/src/utils/typesLocator.ts
 *! THIS FILE NEEDS TO ALWAYS MATCH THE SOURCE
 */

export const enum LocatorType {
    Browser = "browser",
    Windows = "windows",
    Image = "image",
    Java = "java",
}

export type StrategyType = {
    strategy: string;
    value: string;
    matches?: number;
};

export type ElementType = {
    tag: string;
    type?: string;
    modifier?: string | boolean | number;
};

export type IFrameData = {
    name?: string;
    title?: string;
    url?: string;
    sourceURL?: string;
    isMain?: boolean;
    props?: { id?: string; name?: string; class?: string; title?: string };
};

/**
 *
 * @export
 * @interface BrowserLocator
 */
export interface BrowserLocator {
    /**
     *
     * @type {DocType}
     * @memberof BrowserLocator
     */
    type: LocatorType.Browser;
    /**
     *
     * @type {string}
     * @memberof BrowserLocator
     */
    strategy: string;
    /**
     *
     * @type {string}
     * @memberof BrowserLocator
     */
    value: string;
    /**
     *
     * @type {string}
     * @memberof BrowserLocator
     */
    source?: string;
    /**
     *
     * @type {string}
     * @memberof BrowserLocator
     */
    screenshot?: string;
    /**
     *
     * @type {string}
     * @memberof BrowserLocator
     */
    name?: string;
    /**
     *
     * @type {StrategyType[]}
     * @memberof BrowserLocator
     */
    alternatives?: StrategyType[];
    /**
     *
     * @type {ElementType}
     * @memberof BrowserLocator
     */
    element?: ElementType;
    /**
     *
     * @type {IFrameData}
     * @memberof BrowserLocator
     */
    frame?: IFrameData;
}
/**
 *
 * @export
 * @interface WindowsLocator
 */
export interface WindowsLocator {
    /**
     *
     * @type {LocatorType}
     * @memberof WindowsLocator
     */
    type: LocatorType.Windows;
    /**
     *
     * @type {string}
     * @memberof WindowsLocator
     */
    window: string;
    /**
     *
     * @type {string}
     * @memberof WindowsLocator
     */
    value: string;
    /**
     *
     * @type {number}
     * @memberof WindowsLocator
     */
    version: number;
    /**
     *
     * @type {string}
     * @memberof WindowsLocator
     */
    screenshot?: string;
    /**
     *
     * @type {string}
     * @memberof WindowsLocator
     */
    name?: string;
    /**
     *
     * @type {ElementType}
     * @memberof BrowserLocator
     */
    element?: ElementType;
}
/**
 *
 * @export
 * @interface ImageLocator
 */
export interface ImageLocator {
    /**
     *
     * @type {LocatorTypeAll}
     * @memberof ImageLocator
     */
    type: LocatorType.Image;
    /**
     *
     * @type {string}
     * @memberof ImageLocator
     */
    path: string;
    /**
     *
     * @type {number}
     * @memberof ImageLocator
     */
    screenResolutionWidth?: number;
    /**
     *
     * @type {number}
     * @memberof ImageLocator
     */
    screenResolutionHeight?: number;
    /**
     *
     * @type {number}
     * @memberof ImageLocator
     */
    screenPixelRatio?: number;
    /**
     *
     * @type {number}
     * @memberof ImageLocator
     */
    confidence?: number;
    /**
     *
     * @type {string}
     * @memberof ImageLocator
     */
    screenshot: string;
    /**
     *
     * @type {string}
     * @memberof WindowsLocator
     */
    name?: string;
    /**
     *
     * @type {ElementType}
     * @memberof BrowserLocator
     */
    element?: ElementType;
}
/**
 *
 * @export
 * @interface JavaLocator
 */
export interface JavaLocator {
    /**
     *
     * @type {LocatorType}
     * @memberof JavaLocator
     */
    type: LocatorType.Java;
    /**
     *
     * @type {string}
     * @memberof JavaLocator
     */
    window: string;
    /**
     *
     * @type {string}
     * @memberof JavaLocator
     */
    value: string;
    /**
     *
     * @type {number}
     * @memberof JavaLocator
     */
    version: number;
    /**
     *
     * @type {string}
     * @memberof JavaLocator
     */
    screenshot?: string;
    /**
     *
     * @type {string}
     * @memberof JavaLocator
     */
    name?: string;
    /**
     *
     * @type {ElementType}
     * @memberof JavaLocator
     */
    element?: ElementType;
}

export declare type Locator = BrowserLocator | WindowsLocator | ImageLocator | JavaLocator;
export declare type LocatorsMap = {
    [name: string]: Locator;
};
export declare type LocatorsMapWindows = {
    [name: string]: WindowsLocator;
};
export declare type LocatorsMapJava = {
    [name: string]: JavaLocator;
};

// LocatorsArray = [ name, Locator ][]
export declare type LocatorsArray = [string, Locator][];
export declare type LocatorsArrayWindows = [string, WindowsLocator][];
export declare type LocatorsArrayWeb = [string, BrowserLocator][];
export declare type LocatorsArrayImage = [string, ImageLocator][];
export declare type LocatorsArrayJava = [string, JavaLocator][];
