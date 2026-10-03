package com.meditrack.erp;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.text.InputType;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;

public class MainActivity extends AppCompatActivity {

    private static final String PREFS_NAME = "MediTrackPrefs";
    private static final String KEY_SERVER_URL = "server_url";
    private static final int PERMISSION_REQ_CODE = 101;

    private WebView webView;
    private SwipeRefreshLayout swipeRefresh;
    private SharedPreferences prefs;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        webView = findViewById(R.id.webView);
        swipeRefresh = findViewById(R.id.swipeRefresh);

        setupWebView();
        requestRuntimePermissions();

        swipeRefresh.setOnRefreshListener(() -> {
            webView.reload();
            swipeRefresh.setRefreshing(false);
        });

        String savedUrl = prefs.getString(KEY_SERVER_URL, null);
        if (savedUrl == null || savedUrl.trim().isEmpty()) {
            promptServerUrl("http://192.168.1.10:8080");
        } else {
            loadServerUrl(savedUrl);
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void setupWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    showConnectionErrorDialog();
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                MainActivity.this.runOnUiThread(() -> {
                    // Grant camera and microphone permissions for barcode scanner
                    request.grant(request.getResources());
                });
            }
        });
    }

    private void requestRuntimePermissions() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, new String[]{
                    Manifest.permission.CAMERA,
                    Manifest.permission.ACCESS_NETWORK_STATE
            }, PERMISSION_REQ_CODE);
        }
    }

    private void loadServerUrl(String url) {
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            url = "http://" + url;
        }
        webView.loadUrl(url);
    }

    private void promptServerUrl(String defaultVal) {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle(R.string.server_prompt_title);
        builder.setMessage(R.string.server_prompt_msg);

        final EditText input = new EditText(this);
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        input.setText(defaultVal);
        input.setSelection(input.getText().length());
        builder.setView(input);

        builder.setPositiveButton(R.string.action_connect, (dialog, which) -> {
            String url = input.getText().toString().trim();
            if (!url.isEmpty()) {
                if (!url.startsWith("http://") && !url.startsWith("https://")) {
                    url = "http://" + url;
                }
                prefs.edit().putString(KEY_SERVER_URL, url).apply();
                loadServerUrl(url);
            }
        });

        builder.setNegativeButton(R.string.action_cancel, (dialog, which) -> dialog.cancel());
        builder.setCancelable(false);
        builder.show();
    }

    private void showConnectionErrorDialog() {
        new AlertDialog.Builder(this)
                .setTitle("Desktop Not Reachable")
                .setMessage("Unable to connect to your MediTrack desktop ERP.\n\n1. Ensure PC and Phone are on the same Wi-Fi or Mobile Hotspot.\n2. Verify the IP address shown on your desktop screen.")
                .setPositiveButton("Change IP Address", (dialog, which) -> {
                    String current = prefs.getString(KEY_SERVER_URL, "192.168.1.10:8080");
                    promptServerUrl(current);
                })
                .setNegativeButton("Retry", (dialog, which) -> webView.reload())
                .show();
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
