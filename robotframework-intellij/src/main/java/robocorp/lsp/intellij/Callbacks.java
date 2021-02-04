package robocorp.lsp.intellij;

import java.util.Collection;
import java.util.concurrent.CopyOnWriteArraySet;

public class Callbacks<T> {
    public interface ICallback<T> {

        void onCall(T obj);
    }

    private final Collection<ICallback<T>> listeners = new CopyOnWriteArraySet<>();

    public void register(ICallback<T> c) {
        listeners.add(c);
    }

    public void unregister(ICallback<T> c) {
        listeners.remove(c);
    }

    public void onCallback(T obj) {
        for (ICallback<T> c : listeners) {
            c.onCall(obj);
        }
    }
}
