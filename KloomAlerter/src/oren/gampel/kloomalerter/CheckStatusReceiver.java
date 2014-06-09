package oren.gampel.kloomalerter;

import java.io.IOException;
import java.util.regex.Pattern;

import org.apache.http.client.ClientProtocolException;
import org.apache.http.client.HttpClient;
import org.apache.http.client.ResponseHandler;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.impl.client.BasicResponseHandler;
import org.apache.http.impl.client.DefaultHttpClient;

import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.net.Uri;
import android.support.v4.app.NotificationCompat;
import android.util.Log;
import android.widget.Toast;

public class CheckStatusReceiver extends BroadcastReceiver {

    private static final int DELIVERIES_NOTIFICATION_ID = 002;
    private static final String TAG = CheckStatusReceiver.class.getSimpleName();
    private Context ctx;

    @Override
    public void onReceive(Context context, Intent intent) {
	ctx = context;

	Log.i(TAG, "onReceive");

	Toast.makeText(context, "checking status on web", Toast.LENGTH_SHORT).show();

	new Thread(new Runnable() {
	    public void run() {
		checkStatusOnSite();
	    }
	}).start();

    }

    private void checkStatusOnSite() {
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
	} catch (IOException e) {
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

	if (0==counter){
	    mNotifyMgr.cancel(DELIVERIES_NOTIFICATION_ID);
	}

	NotificationCompat.Builder mBuilder = new NotificationCompat.Builder(ctx)
		.setSmallIcon(R.drawable.ic_launcher).setAutoCancel(true)
		.setContentTitle("Packages!!!").setContentText("about " + counter);

	Intent browserIntent = new Intent(Intent.ACTION_VIEW,
		Uri.parse("http://192.168.1.100:5000"));

	// Because clicking the notification opens a new ("special") activity,
	// there's no need to create an artificial back stack.
	PendingIntent resultPendingIntent = PendingIntent.getActivity(ctx, 0,
		browserIntent, PendingIntent.FLAG_UPDATE_CURRENT);

	mBuilder.setContentIntent(resultPendingIntent);

	// Sets an ID for the notification
	int mNotificationId = 002;
	// Builds the notification and issues it.
	mNotifyMgr.notify(mNotificationId, mBuilder.build());
    }
}
