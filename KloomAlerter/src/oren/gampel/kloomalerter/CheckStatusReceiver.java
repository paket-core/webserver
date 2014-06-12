package oren.gampel.kloomalerter;

import java.io.IOException;
import java.util.Date;
import java.util.regex.Pattern;

import org.apache.http.client.ClientProtocolException;
import org.apache.http.client.HttpClient;
import org.apache.http.client.ResponseHandler;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.conn.HttpHostConnectException;
import org.apache.http.impl.client.BasicResponseHandler;
import org.apache.http.impl.client.DefaultHttpClient;

import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.support.v4.app.NotificationCompat;
import android.util.Log;
import android.widget.Toast;

public class CheckStatusReceiver extends BroadcastReceiver {

    private static final int NO_CONNECTION_ALERT_THRESHOLD = 5 * 1000 * 60;
    private static final int DELIVERIES_NOTIFICATION_ID = 002;
    private static final int CONNECTION_NOTIFICATION_ID = 003;
    private static final String TAG = CheckStatusReceiver.class.getSimpleName();
    private String LAST_SUCCESSFULL_PREF = "lastsuccesfulDeliveryTime";
    private Context ctx;

    private long lastsuccesfulDeliveryTime;

    @Override
    public void onReceive(Context context, Intent intent) {
	Log.i(TAG, "onReceive:" + this);
	ctx = context;

	SharedPreferences settings = ctx.getSharedPreferences(MainActivity.PREFS_NAME,
		Context.MODE_PRIVATE);
	lastsuccesfulDeliveryTime = settings.getLong(LAST_SUCCESSFULL_PREF,
		new Date().getTime());

	Toast.makeText(context, "checking status on web", Toast.LENGTH_SHORT).show();

	new Thread(new Runnable() {
	    public void run() {
		try {
		    checkStatusOnSite();

		    lastsuccesfulDeliveryTime = new Date().getTime();
		    SharedPreferences settings = ctx.getSharedPreferences(
			    MainActivity.PREFS_NAME, Context.MODE_PRIVATE);
		    SharedPreferences.Editor editor = settings.edit();
		    editor.putLong(LAST_SUCCESSFULL_PREF, lastsuccesfulDeliveryTime);
		    editor.commit();
		} catch (HttpHostConnectException e) {
		    Log.e(TAG, "Host unavailable");
		} catch (IOException e) {
		    e.printStackTrace();
		}
		long passed = new Date().getTime() - lastsuccesfulDeliveryTime;
		Log.d(TAG, "passed:" + passed);
		notifyOnPassed(passed);
	    }

	    private void notifyOnPassed(long passed) {
		NotificationManager mNotifyMgr = (NotificationManager) ctx
			.getSystemService(Context.NOTIFICATION_SERVICE);

		if (passed < NO_CONNECTION_ALERT_THRESHOLD) {
		    mNotifyMgr.cancel(CONNECTION_NOTIFICATION_ID);
		    return;
		}

		NotificationCompat.Builder mBuilder = new NotificationCompat.Builder(ctx)
			.setSmallIcon(R.drawable.ic_launcher).setAutoCancel(true).setPriority(NotificationCompat.PRIORITY_DEFAULT)
			.setContentTitle("Can't connect to web")
			.setContentText("check intenet connection (" + passed/60000 + " Min)");

		Intent browserIntent = new Intent(android.provider.Settings.ACTION_SETTINGS);
		PendingIntent resultPendingIntent = PendingIntent.getActivity(ctx, 0,
			browserIntent, PendingIntent.FLAG_UPDATE_CURRENT);
		mBuilder.setContentIntent(resultPendingIntent);
		// Builds the notification and issues it.
		mNotifyMgr.notify(CONNECTION_NOTIFICATION_ID, mBuilder.build());

	    }
	}).start();

    }

    private void checkStatusOnSite() throws IOException {
	if (!MainActivity.isNetworkConnected()) {
	    Log.e(TAG, "No connection");
	    return;
	}
	HttpClient client = new DefaultHttpClient();
	HttpGet request = new HttpGet(
		"http://192.168.1.100:5000/deliveriescountinrange.jsonp?callback=jQuery110203478012843988836_1401314328285&lat=32.0853&lng=34.781768&radius=0.045");
	// Get the response
	ResponseHandler<String> responseHandler = new BasicResponseHandler();
	String response_str = null;
	int counter = 0;
	try {
	    response_str = client.execute(request, responseHandler);
	    String[] resp_ = response_str.split(Pattern.quote("("));
	    counter = Integer.parseInt(resp_[1].split(Pattern.quote(")"))[0]);
	    Log.d(TAG, "count: " + counter);
	} catch (ClientProtocolException e) {
	    e.printStackTrace();
	}

	if (counter > 0) {
	    setAlert(counter);
	}
    }

    private void setAlert(int counter) {
	Log.i(TAG, "You got " + counter + " deliveries in range");
	// Gets an instance of the NotificationManager service
	NotificationManager mNotifyMgr = (NotificationManager) ctx
		.getSystemService(Context.NOTIFICATION_SERVICE);

	if (0 == counter) {
	    mNotifyMgr.cancel(DELIVERIES_NOTIFICATION_ID);
	}

	NotificationCompat.Builder mBuilder = new NotificationCompat.Builder(ctx)
		.setSmallIcon(R.drawable.ic_launcher).setAutoCancel(true).setPriority(NotificationCompat.PRIORITY_HIGH)
		.setContentTitle("Packages!!!").setContentText("about " + counter);

	Intent browserIntent = new Intent(Intent.ACTION_VIEW,
		Uri.parse("http://192.168.1.100:5000"));

	// Because clicking the notification opens a new ("special") activity,
	// there's no need to create an artificial back stack.
	PendingIntent resultPendingIntent = PendingIntent.getActivity(ctx, 0,
		browserIntent, PendingIntent.FLAG_UPDATE_CURRENT);

	mBuilder.setContentIntent(resultPendingIntent);

	// Builds the notification and issues it.
	mNotifyMgr.notify(DELIVERIES_NOTIFICATION_ID, mBuilder.build());
    }
}
