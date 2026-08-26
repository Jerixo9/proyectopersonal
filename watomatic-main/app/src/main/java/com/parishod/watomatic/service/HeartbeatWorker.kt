package com.parishod.watomatic.service

import android.content.Context
import android.util.Log
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import com.parishod.watomatic.model.preferences.PreferencesManager
import com.parishod.watomatic.network.PcServerService
import java.util.concurrent.TimeUnit

class HeartbeatWorker(
    context: Context,
    workerParams: WorkerParameters
) : Worker(context, workerParams) {

    override fun doWork(): Result {
        val prefs = PreferencesManager.getPreferencesInstance(applicationContext)
        if (!prefs.isServiceEnabled || !prefs.isPcServerEnabled) {
            return Result.success()
        }

        val pcUrl = prefs.pcServerUrl
        PcServerService.getInstance().sendHeartbeat(pcUrl, "com.whatsapp", object : PcServerService.HeartbeatCallback {
            override fun onSuccess(isOnline: Boolean) {
                Log.d("HeartbeatWorker", "Heartbeat successfully sent to PC: $pcUrl")
            }

            override fun onError(errorMessage: String?) {
                Log.w("HeartbeatWorker", "Failed to send heartbeat to PC: $errorMessage")
            }
        })

        return Result.success()
    }

    companion object {
        private const val WORK_NAME = "pc_server_heartbeat_worker"

        fun schedule(context: Context) {
            val request = PeriodicWorkRequestBuilder<HeartbeatWorker>(15, TimeUnit.MINUTES).build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                request
            )
        }

        fun cancel(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
        }
    }
}
