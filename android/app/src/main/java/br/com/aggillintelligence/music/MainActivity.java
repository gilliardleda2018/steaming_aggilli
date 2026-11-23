package br.com.aggillintelligence.music;
import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebChromeClient;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebSettings;
import android.webkit.WebResourceRequest;
import android.content.Intent;
import android.net.Uri;
public class MainActivity extends Activity {
 private WebView web;
 private static final String HOME="https://server.taila400aa.ts.net/music/";
 @Override public void onCreate(Bundle state) {
  super.onCreate(state);
  web=new WebView(this); setContentView(web);
  WebSettings settings=web.getSettings();
  settings.setJavaScriptEnabled(true);
  settings.setDomStorageEnabled(true);
  settings.setMediaPlaybackRequiresUserGesture(true);
  settings.setAllowFileAccess(false);
  settings.setAllowContentAccess(false);
  web.setWebChromeClient(new WebChromeClient());
  web.setWebViewClient(new WebViewClient(){
   @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request){
    Uri uri=request.getUrl();
    if("https".equals(uri.getScheme()) && "server.taila400aa.ts.net".equals(uri.getHost())) return false;
    try {startActivity(new Intent(Intent.ACTION_VIEW,uri));} catch(Exception ignored){}
    return true;
   }
  });
  if(state==null) {
   web.loadUrl(Uri.parse(HOME).buildUpon()
    .appendQueryParameter("appVersion", BuildConfig.VERSION_NAME).build().toString());
  } else {
   web.restoreState(state);
  }
 }
 @Override public void onBackPressed(){if(web.canGoBack()) web.goBack();else super.onBackPressed();}
 @Override protected void onSaveInstanceState(Bundle state){web.saveState(state);super.onSaveInstanceState(state);}
 @Override protected void onDestroy(){web.destroy();super.onDestroy();}
}
