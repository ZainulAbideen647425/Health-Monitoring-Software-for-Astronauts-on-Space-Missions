package com.astronaut.healthmonitor;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.app.AlertDialog;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothGatt;
import android.bluetooth.BluetoothGattCallback;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattDescriptor;
import android.bluetooth.BluetoothGattService;
import android.bluetooth.BluetoothManager;
import android.bluetooth.le.BluetoothLeScanner;
import android.bluetooth.le.ScanCallback;
import android.bluetooth.le.ScanFilter;
import android.bluetooth.le.ScanResult;
import android.bluetooth.le.ScanSettings;
import android.os.Handler;
import android.os.Looper;
import android.os.ParcelUuid;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/** A thin shell around the dashboard: the app runs on a server whose address the user enters once. */
public class MainActivity extends Activity {
    private static final String START_PAGE = "file:///android_asset/start.html";
    private static final int REQ_CAMERA = 1, REQ_FILE = 2, REQ_BLE = 3;
    private WebView web;
    private SharedPreferences prefs;
    private static final int MAX_RETRIES = 18;
    private int retries = 0;
    private PermissionRequest pendingPermission;
    private ValueCallback<Uri[]> pendingChooser;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences("astro", MODE_PRIVATE);
        web = new WebView(this);
        setContentView(web);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        CookieManager.getInstance().setAcceptCookie(true);
        web.addJavascriptInterface(new Bridge(), "Android");
        web.addJavascriptInterface(new BleBridge(), "AndroidBle");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public void onReceivedError(WebView v, WebResourceRequest r, WebResourceError e) {
                if (!r.isForMainFrame()) return;
                String current = v.getUrl();
                if (current != null && current.startsWith("file:")) return;
                final String target = r.getUrl().toString();
                // A free hosted server sleeps when idle and needs up to a minute to wake: keep retrying quietly.
                if (retries < MAX_RETRIES && target.startsWith("http")) {
                    retries++;
                    v.loadData("<html><body style='background:#0B1220;color:#E6ECF4;font-family:sans-serif;padding:32px'>"
                            + "<h2>Astro Health</h2><p>Waking up the server, please wait...</p>"
                            + "<p style='color:#B9C6D8'>Attempt " + retries + " of " + MAX_RETRIES + "</p></body></html>", "text/html", "utf-8");
                    handler.postDelayed(() -> web.loadUrl(target), 5000);
                    return;
                }
                v.loadUrl(START_PAGE + "?error=1");
            }

            @Override
            public void onPageFinished(WebView v, String url) {
                if (url != null && url.startsWith("http")) retries = 0;
            }
        });
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
        String server = prefs.getString("server", null);
        if (server == null && getString(R.string.default_server).startsWith("http")) server = getString(R.string.default_server);
        web.loadUrl(server == null ? START_PAGE : server);
    }

    @Override
    public void onRequestPermissionsResult(int code, String[] perms, int[] results) {
        if (code == REQ_BLE) {
            boolean all = results.length > 0;
            for (int r : results) if (r != PackageManager.PERMISSION_GRANTED) all = false;
            if (all) scanForSensors(); else bleStatus("error:Bluetooth permission was refused. Allow it in the app settings and try again.");
            return;
        }
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


    // ---- Bluetooth heart rate sensors (standard Heart Rate service 0x180D), passed on to the page ----
    private static final UUID HR_SERVICE = UUID.fromString("0000180d-0000-1000-8000-00805f9b34fb");
    private static final UUID HR_MEASUREMENT = UUID.fromString("00002a37-0000-1000-8000-00805f9b34fb");
    private static final UUID CCC = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb");
    private final Handler handler = new Handler(Looper.getMainLooper());
    private BluetoothGatt gatt;
    private ScanCallback scanCallback;

    private class BleBridge {
        @JavascriptInterface public void start() { runOnUiThread(MainActivity.this::beginBle); }
        @JavascriptInterface public void stop() { runOnUiThread(MainActivity.this::stopBle); }
    }

    private void bleStatus(final String message) {
        final String quoted = org.json.JSONObject.quote(message);
        runOnUiThread(() -> web.evaluateJavascript("window.onNativeBleStatus&&window.onNativeBleStatus(" + quoted + ")", null));
    }

    private void beginBle() {
        stopBle();
        List<String> needed = new ArrayList<>();
        if (Build.VERSION.SDK_INT >= 31) {
            if (checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN) != PackageManager.PERMISSION_GRANTED) needed.add(Manifest.permission.BLUETOOTH_SCAN);
            if (checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) needed.add(Manifest.permission.BLUETOOTH_CONNECT);
        } else if (Build.VERSION.SDK_INT >= 23 && checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            needed.add(Manifest.permission.ACCESS_FINE_LOCATION);
        }
        if (!needed.isEmpty()) {
            requestPermissions(needed.toArray(new String[0]), REQ_BLE);
            return;
        }
        scanForSensors();
    }

    @SuppressWarnings("MissingPermission")
    private void scanForSensors() {
        BluetoothManager manager = (BluetoothManager) getSystemService(BLUETOOTH_SERVICE);
        BluetoothAdapter adapter = manager == null ? null : manager.getAdapter();
        if (adapter == null || !adapter.isEnabled()) { bleStatus("error:Turn Bluetooth on and try again."); return; }
        final BluetoothLeScanner scanner = adapter.getBluetoothLeScanner();
        if (scanner == null) { bleStatus("error:This phone cannot scan for Bluetooth sensors."); return; }
        final List<BluetoothDevice> found = new ArrayList<>();
        bleStatus("Searching for heart rate sensors for 8 seconds...");
        scanCallback = new ScanCallback() {
            @Override public void onScanResult(int type, ScanResult result) {
                for (BluetoothDevice d : found) if (d.getAddress().equals(result.getDevice().getAddress())) return;
                found.add(result.getDevice());
            }
            @Override public void onScanFailed(int errorCode) { bleStatus("error:The Bluetooth search failed (code " + errorCode + ")."); }
        };
        List<ScanFilter> filters = new ArrayList<>();
        filters.add(new ScanFilter.Builder().setServiceUuid(new ParcelUuid(HR_SERVICE)).build());
        scanner.startScan(filters, new ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build(), scanCallback);
        handler.postDelayed(() -> {
            try { scanner.stopScan(scanCallback); } catch (Exception e) { /* already stopped */ }
            scanCallback = null;
            chooseSensor(found);
        }, 8000);
    }

    @SuppressWarnings("MissingPermission")
    private void chooseSensor(final List<BluetoothDevice> found) {
        if (found.isEmpty()) { bleStatus("error:No heart rate sensor was found. Put it on, wake it, and try again."); return; }
        final String[] names = new String[found.size()];
        for (int i = 0; i < names.length; i++) {
            String n = found.get(i).getName();
            names[i] = (n == null ? "Heart rate sensor" : n) + " (" + found.get(i).getAddress() + ")";
        }
        new AlertDialog.Builder(this).setTitle("Choose your sensor").setItems(names, (dialog, which) -> connectTo(found.get(which)))
                .setOnCancelListener(d -> bleStatus("error:No sensor was chosen.")).show();
    }

    @SuppressWarnings({"MissingPermission", "deprecation"})
    private void connectTo(BluetoothDevice device) {
        bleStatus("Connecting to the sensor...");
        gatt = device.connectGatt(this, false, new BluetoothGattCallback() {
            @Override public void onConnectionStateChange(BluetoothGatt g, int status, int newState) {
                if (newState == android.bluetooth.BluetoothProfile.STATE_CONNECTED) g.discoverServices();
                else if (newState == android.bluetooth.BluetoothProfile.STATE_DISCONNECTED) bleStatus("error:The sensor disconnected.");
            }
            @Override public void onServicesDiscovered(BluetoothGatt g, int status) {
                BluetoothGattService service = g.getService(HR_SERVICE);
                BluetoothGattCharacteristic ch = service == null ? null : service.getCharacteristic(HR_MEASUREMENT);
                if (ch == null) { bleStatus("error:This device does not share heart rate."); return; }
                g.setCharacteristicNotification(ch, true);
                BluetoothGattDescriptor descriptor = ch.getDescriptor(CCC);
                if (descriptor != null) {
                    descriptor.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE);
                    g.writeDescriptor(descriptor);
                }
            }
            @Override public void onCharacteristicChanged(BluetoothGatt g, BluetoothGattCharacteristic c) {
                byte[] data = c.getValue();
                if (data == null || data.length < 2) return;
                int value = (data[0] & 1) != 0 && data.length >= 3 ? ((data[1] & 0xff) | ((data[2] & 0xff) << 8)) : (data[1] & 0xff);
                final int bpm = value;
                runOnUiThread(() -> web.evaluateJavascript("window.onNativeHeartRate&&window.onNativeHeartRate(" + bpm + ")", null));
            }
        });
    }

    @SuppressWarnings("MissingPermission")
    private void stopBle() {
        handler.removeCallbacksAndMessages(null);
        try { if (gatt != null) { gatt.disconnect(); gatt.close(); } } catch (Exception e) { /* ignore */ }
        gatt = null;
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) web.goBack(); else super.onBackPressed();
    }

    private class Bridge {
        @JavascriptInterface
        public void saveServer(final String url) {
            runOnUiThread(() -> {
                if (!web.getUrl().startsWith("file:")) return;  // only the start page may change the address
                if (url == null || !url.matches("^https?://[^\\s]+$")) return;
                prefs.edit().putString("server", url).apply();
                web.loadUrl(url);
            });
        }
    }
}
