package oren.gampel.kloomalerter;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;
import android.widget.Toast;

public class CheckStatusActivity extends BroadcastReceiver {
    
    private static final String TAG = CheckStatusActivity.class.getSimpleName();
    
    @Override
    public void onReceive(Context context, Intent intent) {
	Log.i(TAG, "onReceive");
	Toast.makeText(context, "Alarm !!!!!!!!!!", Toast.LENGTH_LONG).show(); // For

    }
}
