package com.parishod.watomatic.network;

import android.os.Build;
import android.util.Log;

import org.json.JSONObject;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

public class PcServerService {
    private static final String TAG = "PcServerService";
    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");
    private static PcServerService instance;
    private final OkHttpClient client;

    private PcServerService() {
        client = new OkHttpClient.Builder()
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(600, TimeUnit.SECONDS)
                .writeTimeout(60, TimeUnit.SECONDS)
                .build();
    }

    public static synchronized PcServerService getInstance() {
        if (instance == null) {
            instance = new PcServerService();
        }
        return instance;
    }

    public interface WebhookCallback {
        void onSuccess(String replyText, boolean isOrderCreated);
        void onError(String errorMessage);
    }

    public interface HeartbeatCallback {
        void onSuccess(boolean isOnline);
        void onError(String errorMessage);
    }

    /**
     * Envía el mensaje recibido de WhatsApp al servidor PC.
     */
    public void sendWebhookMessage(String serverBaseUrl, String sender, String message, String packageName, WebhookCallback callback) {
        String url = normalizeUrl(serverBaseUrl) + "api/webhook";
        try {
            JSONObject json = new JSONObject();
            json.put("sender", sender);
            json.put("message", message);
            json.put("package", packageName != null ? packageName : "com.whatsapp");

            RequestBody body = RequestBody.create(json.toString(), JSON);
            Request request = new Request.Builder()
                    .url(url)
                    .post(body)
                    .build();

            client.newCall(request).enqueue(new Callback() {
                @Override
                public void onFailure(Call call, IOException e) {
                    Log.e(TAG, "Webhook call failed: " + e.getMessage());
                    if (callback != null) {
                        callback.onError(e.getMessage());
                    }
                }

                @Override
                public void onResponse(Call call, Response response) throws IOException {
                    if (!response.isSuccessful()) {
                        if (callback != null) {
                            callback.onError("HTTP Error: " + response.code());
                        }
                        return;
                    }

                    try {
                        String respBody = response.body() != null ? response.body().string() : "";
                        JSONObject respJson = new JSONObject(respBody);
                        String reply = respJson.optString("reply", "");
                        boolean orderCreated = respJson.optBoolean("order_created", false);
                        
                        if (callback != null) {
                            callback.onSuccess(reply, orderCreated);
                        }
                    } catch (Exception e) {
                        Log.e(TAG, "Error parsing webhook response: " + e.getMessage());
                        if (callback != null) {
                            callback.onError("Parse error: " + e.getMessage());
                        }
                    }
                }
            });
        } catch (Exception e) {
            Log.e(TAG, "Error building webhook request: " + e.getMessage());
            if (callback != null) {
                callback.onError(e.getMessage());
            }
        }
    }

    /**
     * Envía un ping de Heartbeat al servidor PC para reportar que el teléfono está conectado.
     */
    public void sendHeartbeat(String serverBaseUrl, String packageName, HeartbeatCallback callback) {
        String url = normalizeUrl(serverBaseUrl) + "api/heartbeat";
        try {
            JSONObject json = new JSONObject();
            json.put("device_name", Build.MANUFACTURER + " " + Build.MODEL);
            json.put("package", packageName != null ? packageName : "com.whatsapp");
            json.put("status", "active");

            RequestBody body = RequestBody.create(json.toString(), JSON);
            Request request = new Request.Builder()
                    .url(url)
                    .post(body)
                    .build();

            client.newCall(request).enqueue(new Callback() {
                @Override
                public void onFailure(Call call, IOException e) {
                    Log.d(TAG, "Heartbeat failed: " + e.getMessage());
                    if (callback != null) {
                        callback.onError(e.getMessage());
                    }
                }

                @Override
                public void onResponse(Call call, Response response) throws IOException {
                    boolean success = response.isSuccessful();
                    if (callback != null) {
                        if (success) {
                            callback.onSuccess(true);
                        } else {
                            callback.onError("Status: " + response.code());
                        }
                    }
                }
            });
        } catch (Exception e) {
            Log.e(TAG, "Error building heartbeat: " + e.getMessage());
            if (callback != null) {
                callback.onError(e.getMessage());
            }
        }
    }

    private String normalizeUrl(String baseUrl) {
        if (baseUrl == null || baseUrl.trim().isEmpty()) {
            return "http://192.168.1.100:8000/";
        }
        baseUrl = baseUrl.trim();
        if (!baseUrl.startsWith("http://") && !baseUrl.startsWith("https://")) {
            baseUrl = "http://" + baseUrl;
        }
        if (!baseUrl.endsWith("/")) {
            baseUrl = baseUrl + "/";
        }
        return baseUrl;
    }
}
