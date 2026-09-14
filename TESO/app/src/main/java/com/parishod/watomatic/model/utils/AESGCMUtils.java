package com.parishod.watomatic.model.utils;

import android.util.Base64;
import android.util.Log;

import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public class AESGCMUtils {
    private static final String TAG = "AESGCMUtils";
    private static final String ALGORITHM = "AES/GCM/NoPadding";
    private static final int GCM_IV_LENGTH = 12;
    private static final int GCM_TAG_LENGTH = 128; // bits
    
    // IMPORTANTE: Esta clave debe coincidir exactamente con la de la PC (backend/crypto_utils.py)
    private static final byte[] SECRET_KEY_BYTES = "watomatic_secure_key_12345678901".getBytes(StandardCharsets.UTF_8);

    public static JSONObject encryptPayload(JSONObject data) {
        try {
            SecretKeySpec keySpec = new SecretKeySpec(SECRET_KEY_BYTES, "AES");
            
            // Generar IV aleatorio (12 bytes)
            byte[] iv = new byte[GCM_IV_LENGTH];
            new SecureRandom().nextBytes(iv);
            
            GCMParameterSpec gcmParameterSpec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
            
            Cipher cipher = Cipher.getInstance(ALGORITHM);
            cipher.init(Cipher.ENCRYPT_MODE, keySpec, gcmParameterSpec);
            
            byte[] cipherText = cipher.doFinal(data.toString().getBytes(StandardCharsets.UTF_8));
            
            JSONObject result = new JSONObject();
            result.put("iv", Base64.encodeToString(iv, Base64.NO_WRAP));
            result.put("data", Base64.encodeToString(cipherText, Base64.NO_WRAP));
            return result;
            
        } catch (Exception e) {
            Log.e(TAG, "Error encrypting payload", e);
            return null;
        }
    }

    public static JSONObject decryptPayload(JSONObject encryptedData) {
        try {
            if (!encryptedData.has("iv") || !encryptedData.has("data")) {
                Log.e(TAG, "Missing iv or data in encrypted payload");
                return null;
            }
            
            byte[] iv = Base64.decode(encryptedData.getString("iv"), Base64.NO_WRAP);
            byte[] cipherText = Base64.decode(encryptedData.getString("data"), Base64.NO_WRAP);
            
            SecretKeySpec keySpec = new SecretKeySpec(SECRET_KEY_BYTES, "AES");
            GCMParameterSpec gcmParameterSpec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
            
            Cipher cipher = Cipher.getInstance(ALGORITHM);
            cipher.init(Cipher.DECRYPT_MODE, keySpec, gcmParameterSpec);
            
            byte[] decryptedText = cipher.doFinal(cipherText);
            
            return new JSONObject(new String(decryptedText, StandardCharsets.UTF_8));
            
        } catch (Exception e) {
            Log.e(TAG, "Error decrypting payload", e);
            return null;
        }
    }
}
