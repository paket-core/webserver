package oren.gampel.kloomalerter;

import android.app.Service;
import android.content.Intent;
import android.os.IBinder;
import android.util.Log;
import android.widget.Toast;

/**
 * now in git!
 */
public class AlertsService extends Service {

    private static final String TAG = AlertsService.class.getSimpleName();

    @Override
    public void onCreate() {
	Log.i(TAG, "onCreate ");
	super.onCreate();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
	Log.i(TAG, "onStartCommand email: " + intent.getExtras().get("email"));
	Toast.makeText(this, "Service start - onStartCommand", Toast.LENGTH_SHORT).show();
	
	try {
	    Thread.sleep(3000);
	} catch (InterruptedException e) {
	    // TODO Auto-generated catch block
	    e.printStackTrace();
	}
	
	return Service.START_REDELIVER_INTENT;
    }

    @Override
    public void onStart(Intent intent, int startId) {
	Log.i(TAG, "onStart email: " + intent.getExtras().get("email"));
	Toast.makeText(this, "Service start - onStart", Toast.LENGTH_SHORT).show();
    }

    @Override
    public void onDestroy() {
	Log.i(TAG, "onDestroy");
	Toast.makeText(this, "Service stoped", Toast.LENGTH_SHORT).show();
	super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
	// TODO for communication return IBinder implementation
	return null;
    }
}
