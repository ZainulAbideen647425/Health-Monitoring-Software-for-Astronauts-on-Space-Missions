package com.astronaut.healthmonitor;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.webkit.CookieManager;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.net.InetSocketAddress;
import java.net.Socket;

/** Runs the whole app on the phone: a Python server on 127.0.0.1 and a WebView showing it. */
public class MainActivity extends Activity {
    private static final String HOME = "http://localhost:8000/";
    private static final int REQ_CAMERA = 1, REQ_FILE = 2;
    private WebView web;
    private PermissionRequest pendingPermission;
    private ValueCallback<Uri[]> pendingChooser;
    private static boolean serverStarted = false;

    private static String page(String title, String body) {
        return "<html><body style='margin:0;padding:28px;background:#0e1416;color:#eee;font-family:sans-serif'>"
                + "<h2>" + title + "</h2><p style='color:#aab;line-height:1.5'>" + body + "</p></body></html>";
    }

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        web = new WebView(this);
        setContentView(web);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        CookieManager.getInstance().setAcceptCookie(true);
        web.setWebViewClient(new WebViewClient());
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(() -> {
                    if (Build.VERSION.SDK_INT >= 23 && checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
                        pendingPermission = request;
                        requestPermissions(new String[]{Manifest.permission.CAMERA}, REQ_CAMERA);
                    } else {
                        request.grant(request.getResources());
                    }
                });
            }

            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (pendingChooser != null) pendingChooser.onReceiveValue(null);
                pendingChooser = callback;
                Intent pick = new Intent(Intent.ACTION_GET_CONTENT);
                pick.addCategory(Intent.CATEGORY_OPENABLE);
                pick.setType("*/*");
                startActivityForResult(Intent.createChooser(pick, "Choose a CSV file"), REQ_FILE);
                return true;
            }
        });
        web.loadData(page("Astro Health", "Starting the health monitor on your phone. The first start can take up to a minute."), "text/html", "utf-8");
        new Thread(this::startServerAndOpen).start();
    }

    private void show(final String html) {
        runOnUiThread(() -> web.loadDataWithBaseURL(null, html, "text/html", "utf-8", null));
    }

    private boolean portOpen() {
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress("127.0.0.1", 8000), 300);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private void startServerAndOpen() {
        PyObject entry;
        try {
            if (!Python.isStarted()) Python.start(new AndroidPlatform(this));
            entry = Python.getInstance().getModule("android_entry");
            if (!serverStarted && !portOpen()) {
                entry.callAttr("start", getFilesDir().getAbsolutePath());
                serverStarted = true;
            }
        } catch (Throwable t) {
            show(page("Could not start", "The built-in server failed to start:<br><pre style='white-space:pre-wrap;font-size:12px'>" + escape(String.valueOf(t)) + "</pre>"));
            return;
        }
        for (int i = 0; i < 180; i++) {
            if (portOpen()) {
                runOnUiThread(() -> web.loadUrl(HOME));
                return;
            }
            String error = entry.callAttr("last_error").toString();
            if (!error.isEmpty()) {
                show(page("Could not start", "The built-in server stopped:<br><pre style='white-space:pre-wrap;font-size:11px'>" + escape(error) + "</pre>"));
                return;
            }
            try { Thread.sleep(500); } catch (InterruptedException e) { return; }
        }
        show(page("Still starting", "The server did not answer in time. Close the app completely and open it again."));
    }

    private static String escape(String text) {
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }

    @Override
    public void onRequestPermissionsResult(int code, String[] perms, int[] results) {
        if (code == REQ_CAMERA && pendingPermission != null) {
            if (results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) {
                pendingPermission.grant(pendingPermission.getResources());
            } else {
                pendingPermission.deny();
            }
            pendingPermission = null;
        }
    }

    @Override
    protected void onActivityResult(int code, int result, Intent data) {
        if (code == REQ_FILE && pendingChooser != null) {
            Uri[] picked = null;
            if (result == RESULT_OK && data != null && data.getData() != null) picked = new Uri[]{data.getData()};
            pendingChooser.onReceiveValue(picked);
            pendingChooser = null;
        }
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) web.goBack(); else super.onBackPressed();
    }
}
