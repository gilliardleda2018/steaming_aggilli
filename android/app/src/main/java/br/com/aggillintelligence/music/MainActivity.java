package br.com.aggillintelligence.music;
import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.webkit.WebChromeClient;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebSettings;
import android.webkit.WebResourceRequest;
import android.content.Intent;
import android.net.Uri;
import androidx.webkit.JavaScriptReplyProxy;
import androidx.webkit.WebViewCompat;
import androidx.webkit.WebViewFeature;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Locale;
import org.json.JSONException;
import org.json.JSONObject;
public class MainActivity extends Activity {
 private WebView web;
 private static final String HOME="https://server.taila400aa.ts.net/music/";
 private static final String ORIGIN="https://server.taila400aa.ts.net";
 private static final int MIC_REQUEST=41;
 // Ponte de voz: o WebView do Android não reconhece fala pela Web Speech API.
 private SpeechRecognizer recognizer;
 private JavaScriptReplyProxy voiceReply;
 // Resposta falada da ANI ("Tocando ..."), como uma assistente de voz.
 private TextToSpeech speech;
 private boolean speechReady;
 private String pendingSpeech;
 @Override public void onCreate(Bundle state) {
  super.onCreate(state);
  web=new WebView(this); setContentView(web);
  WebSettings settings=web.getSettings();
  settings.setJavaScriptEnabled(true);
  settings.setDomStorageEnabled(true);
  // Pedidos por voz começam a tocar sem um toque extra na tela.
  settings.setMediaPlaybackRequiresUserGesture(false);
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
  if(WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER)){
   // Só a página principal do player recebe a ponte; iframes, como o do YouTube, ficam de fora.
   WebViewCompat.addWebMessageListener(web,"AggilliVoice",Collections.singleton(ORIGIN),
    (view,message,sourceOrigin,isMainFrame,replyProxy)->{
     if(!isMainFrame||message.getData()==null)return;
     voiceReply=replyProxy;
     String data=message.getData();
     if("start".equals(data))startVoice();
     else if("cancel".equals(data))cancelVoice();
     else if(data.startsWith("say:"))say(data.substring(4));
    });
  }
  if(state==null) {
   web.loadUrl(Uri.parse(HOME).buildUpon()
    .appendQueryParameter("appVersion", BuildConfig.VERSION_NAME).build().toString());
  } else {
   web.restoreState(state);
  }
 }
 private void startVoice(){
  if(!SpeechRecognizer.isRecognitionAvailable(this)){sendVoice("error","unavailable");return;}
  if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED){
   requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},MIC_REQUEST);
   return;
  }
  cancelVoice();
  recognizer=SpeechRecognizer.createSpeechRecognizer(this);
  recognizer.setRecognitionListener(new RecognitionListener(){
   @Override public void onResults(Bundle results){
    ArrayList<String> texts=results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
    if(texts==null||texts.isEmpty())sendVoice("error","nomatch");
    else sendVoice("result",texts.get(0));
    releaseRecognizer();
   }
   @Override public void onError(int error){
    String reason;
    if(error==SpeechRecognizer.ERROR_NO_MATCH||error==SpeechRecognizer.ERROR_SPEECH_TIMEOUT)reason="nomatch";
    else if(error==SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS)reason="denied";
    else reason="failed";
    sendVoice("error",reason);
    releaseRecognizer();
   }
   @Override public void onReadyForSpeech(Bundle params){}
   @Override public void onBeginningOfSpeech(){}
   @Override public void onRmsChanged(float rmsdB){}
   @Override public void onBufferReceived(byte[] buffer){}
   @Override public void onEndOfSpeech(){}
   @Override public void onPartialResults(Bundle partialResults){}
   @Override public void onEvent(int eventType,Bundle params){}
  });
  Intent intent=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
  intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
  intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE,"pt-BR");
  intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS,1);
  recognizer.startListening(intent);
 }
 private void say(String text){
  text=text.replaceAll("\\s+"," ").trim();
  if(text.length()>240)text=text.substring(0,240);
  if(text.isEmpty()){sendSpoken();return;}
  if(speech==null){
   pendingSpeech=text;
   speech=new TextToSpeech(this,status->{
    speechReady=status==TextToSpeech.SUCCESS
     &&speech.setLanguage(new Locale("pt","BR"))>=TextToSpeech.LANG_AVAILABLE;
    if(!speechReady){sendSpoken();return;}
    speech.setOnUtteranceProgressListener(new UtteranceProgressListener(){
     @Override public void onStart(String id){}
     @Override public void onDone(String id){sendSpoken();}
     @Override public void onError(String id){sendSpoken();}
    });
    String next=pendingSpeech;pendingSpeech=null;
    if(next!=null)speech.speak(next,TextToSpeech.QUEUE_FLUSH,null,"ani");
   });
   return;
  }
  if(!speechReady){sendSpoken();return;}
  speech.speak(text,TextToSpeech.QUEUE_FLUSH,null,"ani");
 }
 private void sendSpoken(){
  runOnUiThread(()->{
   if(voiceReply==null)return;
   try{voiceReply.postMessage(new JSONObject().put("type","spoken").toString());}catch(JSONException ignored){}
  });
 }
 private void cancelVoice(){
  if(recognizer!=null)recognizer.cancel();
  releaseRecognizer();
 }
 private void releaseRecognizer(){
  if(recognizer==null)return;
  recognizer.destroy();
  recognizer=null;
 }
 private void sendVoice(String type,String value){
  if(voiceReply==null)return;
  try{
   JSONObject data=new JSONObject().put("type",type);
   data.put("result".equals(type)?"text":"reason",value);
   voiceReply.postMessage(data.toString());
  }catch(JSONException ignored){}
 }
 @Override public void onRequestPermissionsResult(int requestCode,String[] permissions,int[] results){
  super.onRequestPermissionsResult(requestCode,permissions,results);
  if(requestCode!=MIC_REQUEST)return;
  if(results.length>0&&results[0]==PackageManager.PERMISSION_GRANTED)startVoice();
  else sendVoice("error","denied");
 }
 @Override protected void onPause(){cancelVoice();super.onPause();}
 @Override public void onBackPressed(){if(web.canGoBack()) web.goBack();else super.onBackPressed();}
 @Override protected void onSaveInstanceState(Bundle state){web.saveState(state);super.onSaveInstanceState(state);}
 @Override protected void onDestroy(){
  releaseRecognizer();
  if(speech!=null){speech.stop();speech.shutdown();speech=null;}
  web.destroy();super.onDestroy();
 }
}
