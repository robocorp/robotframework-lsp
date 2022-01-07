export class WeakValueMap<K, V extends object> {
    // TODO: We could improve to remove from the map to clear the memory related
    // to entries with a FinalizationRegistry, but let's keep it simple for now...
    private map = new Map<K, WeakRef<V>>();

    public get(key: K): V | undefined {
        const w = this.map.get(key);
        if (w !== undefined) {
            return w.deref();
        }
        return undefined;
    }

    public set(key: K, value: V) {
        const ref = new WeakRef(value);
        this.map.set(key, ref);
    }

    public delete(key: K) {
        this.map.delete(key);
    }
}
