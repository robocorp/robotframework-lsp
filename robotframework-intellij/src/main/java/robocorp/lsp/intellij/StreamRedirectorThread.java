package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

public final class StreamRedirectorThread extends Thread {

    private static final Logger LOG = Logger.getInstance(StreamRedirectorThread.class);

    private final InputStream is;
    private final OutputStream out;

    public StreamRedirectorThread(InputStream is, OutputStream out) {
        this.setName("ThreadStreamReader");
        this.setDaemon(true);
        this.is = is;
        this.out = out;
    }

    @Override
    public void run() {
        try {
            int i;
            byte[] buf = new byte[80];

            while ((i = is.read(buf)) != -1) {
                this.out.write(buf, 0, i);
            }
        } catch (IOException e) {
        }
    }

}
