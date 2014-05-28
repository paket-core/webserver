package oren.gampel.kloomalerter;

import java.io.IOException;

import org.apache.http.client.ClientProtocolException;
import org.apache.http.client.HttpClient;
import org.apache.http.client.ResponseHandler;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.impl.client.BasicResponseHandler;
import org.apache.http.impl.client.DefaultHttpClient;

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

	Toast.makeText(context, "checking status on web", Toast.LENGTH_SHORT).show();
	
	new Thread(new Runnable() {
	    public void run() {
		checkStatusOnSite();
	    }
	}).start();

    }

    private void checkStatusOnSite() {
	HttpClient client = new DefaultHttpClient();
	HttpGet request = new HttpGet("http://192.168.1.100:5000/verify?email="
		+ "oren@orengampel.com");
	// Get the response
	ResponseHandler<String> responseHandler = new BasicResponseHandler();
	String response_str = null;
	try {
	    response_str = client.execute(request, responseHandler);
	} catch (ClientProtocolException e) {
	    e.printStackTrace();
	} catch (IOException e) {
	    e.printStackTrace();
	}

	Log.d(TAG, "web: " + response_str);
    }
}
