/**
 * @source https://github.com/robocorp/inspector-ext/blob/master/src/utils/types.ts
 *! THIS FILE NEEDS TO ALWAYS MATCH THE SOURCE
 */

export declare enum LocatorType {
    Browser = "browser",
    Windows = "windows",
    Image = "image",
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
    isMain?: boolean;
    props?: { id?: string; name?: string; class?: string; title?: string };
};

/**
 * @interface LOCATORS
 */

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
    value: string;
    /**
     *
     * @type {string}
     * @memberof ImageLocator
     */
    path?: string;
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

export declare type Locator = BrowserLocator | WindowsLocator | ImageLocator;
export declare type LocatorsMap = {
    [name: string]: Locator;
};
export declare type LocatorsMapWindows = {
    [name: string]: WindowsLocator;
};
// LocatorsArray = [ name, Locator ][]
export declare type LocatorsArray = [string, Locator][];
export declare type LocatorsArrayWindows = [string, WindowsLocator][];
export declare type LocatorsArrayWeb = [string, BrowserLocator][];
