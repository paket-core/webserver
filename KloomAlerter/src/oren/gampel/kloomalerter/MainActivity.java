package oren.gampel.kloomalerter;

import java.io.IOException;

import org.apache.http.client.ClientProtocolException;
import org.apache.http.client.HttpClient;
import org.apache.http.client.ResponseHandler;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.impl.client.BasicResponseHandler;
import org.apache.http.impl.client.DefaultHttpClient;

import android.accounts.Account;
import android.accounts.AccountManager;
import android.app.Activity;
import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.os.AsyncTask;
import android.os.Bundle;
import android.os.StrictMode;
import android.os.SystemClock;
import android.util.Log;
import android.view.Menu;
import android.view.MenuItem;
import android.widget.CheckBox;
import android.widget.CompoundButton;
import android.widget.CompoundButton.OnCheckedChangeListener;
import android.widget.TextView;

public class MainActivity extends Activity {

    private static final String TAG = MainActivity.class.getSimpleName();

    private TextView accontNameView;
    private CheckBox checkBoxAlerts;
    private AlarmManager alarmMgr;
    private PendingIntent checkStatusIntent;

    private static ConnectivityManager connectivityManager;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
	// setStrictMode();
	super.onCreate(savedInstanceState);
	setContentView(R.layout.fragment_main);

	connectivityManager = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);

	alarmMgr = (AlarmManager) getSystemService(Context.ALARM_SERVICE);
	Intent intent = new Intent(getBaseContext(), CheckStatusReceiver.class);
	checkStatusIntent = PendingIntent.getBroadcast(getBaseContext(), 0, intent, 0);
    }

    @Override
    protected void onStart() {
	super.onStart();
	Log.i(TAG, "onStart");
	accontNameView = (TextView) findViewById(R.id.account);
	checkBoxAlerts = (CheckBox) findViewById(R.id.checkBoxAlerts);

	checkBoxAlerts.setChecked(false);
	checkBoxAlerts.setEnabled(false);

	checkBoxAlerts.setOnCheckedChangeListener(new OnCheckedChangeListener() {

	    @Override
	    public void onCheckedChanged(CompoundButton buttonView, boolean isChecked) {
		Log.i(TAG, "onCheckedChanged " + isChecked);
		if (isChecked) {
		    alarmMgr.setRepeating(AlarmManager.ELAPSED_REALTIME_WAKEUP,
			    SystemClock.elapsedRealtime() + 3 * 1000, 7 * 1000,
			    checkStatusIntent);
		} else {
		    alarmMgr.cancel(checkStatusIntent);
		}
	    }

	});

	accontNameView.setText("wait...");
	new GetValidAccounts().execute(this);

	// // Start the service
	// Intent i = new Intent(this, AlertsService.class);
	// // potentially add data to the intent
	// i.putExtra("KEY1", "Value to be used by the service");
	// this.startService(i);

    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {

	// Inflate the menu; this adds items to the action bar if it is present.
	getMenuInflater().inflate(R.menu.main, menu);
	return true;
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
	// Handle action bar item clicks here. The action bar will
	// automatically handle clicks on the Home/Up button, so long
	// as you specify a parent activity in AndroidManifest.xml.
	int id = item.getItemId();
	if (id == R.id.action_settings) {
	    return true;
	}
	return super.onOptionsItemSelected(item);
    }

    /**
     * This AsyncTask runs at a separate thread from the UI thread, but can
     * safely access it.
     */
    private class GetValidAccounts extends AsyncTask<Context, String, String> {

	private static final String NO_ACCOUNT_FOUND = "No account found";

	@Override
	protected String doInBackground(Context... ctx) {
	    Account[] accounts = AccountManager.get(MainActivity.this).getAccounts();
	    for (Account account : accounts) {
		Log.i(TAG, "acc  type:" + account.type + " acc name:" + account.name);
		// TODO for now use the first account encountered
		try {
		    if (isValidAccount(account)) {
			return account.name;
		    }
		} catch (Exception e) {
		    e.printStackTrace();
		    return e.getMessage();
		}
	    }
	    return NO_ACCOUNT_FOUND;
	}

	/**
	 * Call the server to check if account is valid.
	 * 
	 * @param account
	 * @return whether the account is valid
	 * @throws IOException
	 * @throws ClientProtocolException
	 */
	private boolean isValidAccount(Account account) throws ClientProtocolException,
		IOException {
	    // TODO for now we only use email address. Improve check. (or
	    // remove?)
	    String accountName = account.name;
	    publishProgress("Checking: " + accountName + "...");

	    try {
		Thread.sleep(500);
	    } catch (InterruptedException e) {
		// TODO Auto-generated catch block
		e.printStackTrace();
	    }

	    if (!accountName.contains("@")) {
		Log.d(TAG, "invalid:" + account);
		return false;
	    }

	    if (isNetworkConnected() == false) {
		Log.d(TAG, "No connection");
		return false;
	    }
	    HttpClient client = new DefaultHttpClient();
	    HttpGet request = new HttpGet("http://192.168.1.100:5000/verify?email="
		    + accountName);
	    // Get the response
	    ResponseHandler<String> responseHandler = new BasicResponseHandler();
	    String response_str = null;
	    response_str = client.execute(request, responseHandler);
	    if (response_str.equalsIgnoreCase("True")) {
		return true;
	    }
	    Log.d(TAG, "Response: " + response_str);
	    return false;
	}

	@Override
	protected void onPostExecute(String accountName) {
	    Log.i(TAG, "onPostExecute:" + accountName);
	    accontNameView.setText(accountName);
	    if (accountName.equals(NO_ACCOUNT_FOUND)) {
		checkBoxAlerts.setChecked(false);
		checkBoxAlerts.setEnabled(true); // FIXME just for debug
	    } else {
		checkBoxAlerts.setChecked(true);
		checkBoxAlerts.setEnabled(true);
	    }

	}

	@Override
	protected void onProgressUpdate(String... prog) {
	    Log.i(TAG, "onProgressUpdate:" + prog[0]);
	    accontNameView.setText(prog[0]);
	}

    }

    @SuppressWarnings("unused")
    private void setStrictMode() {
	StrictMode.setThreadPolicy(new StrictMode.ThreadPolicy.Builder()
		.detectDiskReads().detectDiskWrites().detectNetwork() // or
								      // .detectAll()
								      // for
								      // all
								      // detectable
								      // problems
		.penaltyLog().build());
    }

    // Check network connection
    static boolean isNetworkConnected() {
	NetworkInfo activeNetworkInfo = connectivityManager.getActiveNetworkInfo();
	return activeNetworkInfo != null && activeNetworkInfo.isConnected();
    }

}
