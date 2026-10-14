"""Android pack (OWASP Mobile Top 10 2024 / MASVS v2 checklist): AndroidManifest.xml and network
security config (config engine on the flattened XML), Kotlin app code (tree-sitter) and the release
build script. Detection and wording are crev's own; citations are the Android developer docs
(reference pages and the "Security risks" pages, which name the MASVS category) and OWASP MAS."""
from specs._common import Pack

P = Pack("ANDROID", "kotlin", "Android developer docs (API 36)", {"any": "*"})
RISK = "https://developer.android.com/privacy-and-security/risks/"
APPEL = "https://developer.android.com/guide/topics/manifest/application-element"
NSC = "https://developer.android.com/privacy-and-security/security-config"
WV = "https://developer.android.com/reference/android/webkit/WebView"
WS = "https://developer.android.com/reference/android/webkit/WebSettings"
CTX = "https://developer.android.com/reference/android/content/Context"
MANIFEST = ["**/AndroidManifest.xml"]
NSC_FILES = ["**/res/xml/*.xml"]
KT = ["**/*.kt"]
KTS = ["**/build.gradle.kts"]
GROOVY = ["**/build.gradle"]

MF = lambda app_attrs, body="": ('<?xml version="1.0" encoding="utf-8"?>\n<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n'
                                 f'  <application{app_attrs}>\n{body}  </application>\n</manifest>\n')
NS = lambda body: '<?xml version="1.0" encoding="utf-8"?>\n<network-security-config>\n' + body + '</network-security-config>\n'


def sec(id, title, url, needle, query, bad, good, msg, sev="major", **kw):
    kw.setdefault("files", KT)
    P(id, title, url, needle, query, bad, good, msg, sev=sev, kind="security", cat="security", **kw)


def manifest(id, title, url, needle, cfg, bad, good, msg, sev="major", files=MANIFEST, **kw):
    P(id, title, url, needle, None, bad, good, msg, sev=sev, kind="security", cat="security", lang="xml", engine="config",
      config=cfg, files=files, **kw)


# ------------------------------------------------------------------ manifest / network security config
manifest("DEBUGGABLE", "android:debuggable=\"true\" in the manifest", RISK + "android-debuggable",
         "Allowing the application to be debuggable in itself is not a vulnerability, but it does expose the application to greater risk",
         {"key": "manifest.application.@debuggable", "op": "equals", "value": "true", "case_insensitive": True},
         MF(' android:debuggable="true"'), MF(' android:label="@string/app_name"'),
         "A debuggable release lets anyone with adb attach a debugger, run code as the app (run-as) and read its private files. Leave debuggable to the build type (debug builds set it automatically).",
         sev="critical", cwe=["CWE-489"], docv="Android security risks")
manifest("CLEARTEXT-TRAFFIC", "android:usesCleartextTraffic=\"true\"", APPEL, "Indicates whether the app intends to use cleartext network traffic",
         {"key": "manifest.application.@usesCleartextTraffic", "op": "equals", "value": "true", "case_insensitive": True},
         MF(' android:usesCleartextTraffic="true"'), MF(' android:networkSecurityConfig="@xml/network_security_config"'),
         "Cleartext HTTP is allowed for every host. Traffic can be read and changed on the network; use HTTPS, and if one legacy host needs HTTP allow only that domain in a network security config.",
         cwe=["CWE-319"], docv="Android manifest reference")
manifest("ALLOW-BACKUP", "android:allowBackup=\"true\" without backup rules", RISK + "backup-best-practices",
         "The common theme is that these recommendations aim at ensuring that no sensitive data is leaked",
         {"key": "manifest.application", "op": "matches", "value": r"\ballowBackup=true\b", "unless_value": r"\b(fullBackupContent|dataExtractionRules)="},
         MF(' android:allowBackup="true"'), MF(' android:allowBackup="true" android:dataExtractionRules="@xml/data_extraction_rules"'),
         "Backups copy the app's private files and databases off the device. Exclude tokens and personal data with dataExtractionRules / fullBackupContent, or turn backup off.",
         sev="minor", mode="ai-confirm", ai="Does the app keep credentials, tokens or personal data in files, databases or shared preferences that this backup would include?",
         cwe=["CWE-530"], docv="Android security risks")
manifest("EXPORTED-NO-PERMISSION", "Component exported without a permission", RISK + "android-exported",
         "If true , any app can access the activity and launch it by its exact class name",
         {"key_re": r"^manifest\.application\.(activity|activity-alias|service|receiver|provider)(#\d+)?$", "op": "matches", "value": r"\bexported=true\b", "unless_value": r"\bpermission=",
          "unless_child": r"intent-filter(#\d+)?\.category(#\d+)?\.@name=android\.intent\.category\.(LAUNCHER|HOME|LEANBACK_LAUNCHER)$"},
         MF("", '    <service android:name=".SyncService" android:exported="true"/>\n'),
         MF("", '    <service android:name=".SyncService" android:exported="true" android:permission="com.example.permission.SYNC"/>\n'),
         "Any installed app can start this component and pass it data. Set exported=\"false\", or protect it with a signature-level permission and validate every intent extra.",
         mode="ai-confirm", ai="Is this component meant to be reachable by arbitrary apps (a launcher activity, a public share target) or does it expose internal functionality or data?",
         cwe=["CWE-926"], docv="Android security risks", precision="low",
         fp=[MF("", '    <activity android:name=".MainActivity" android:exported="true">\n      <intent-filter>\n        <action android:name="android.intent.action.MAIN"/>\n        <category android:name="android.intent.category.LAUNCHER"/>\n      </intent-filter>\n    </activity>\n')])
manifest("NSC-CLEARTEXT", "Network security config permits cleartext", NSC, "cleartextTrafficPermitted",
         {"key_re": r"^network-security-config\.(base-config|domain-config(#\d+)?)\.@cleartextTrafficPermitted$", "op": "equals", "value": "true", "case_insensitive": True},
         NS('  <base-config cleartextTrafficPermitted="true"/>\n'), NS('  <base-config cleartextTrafficPermitted="false"/>\n'),
         "Cleartext HTTP is allowed by the network security config. Keep it off in base-config; if a host truly needs HTTP, allow only that domain and only in debug overrides.",
         files=NSC_FILES, cwe=["CWE-319"], docv="Android network security configuration")
manifest("NSC-USER-CA", "Network security config trusts user-installed CAs", NSC, 'src="user"',
         {"key_re": r"^network-security-config\.(base-config|domain-config(#\d+)?)\.trust-anchors\.certificates(#\d+)?\.@src$", "op": "equals", "value": "user"},
         NS('  <base-config>\n    <trust-anchors>\n      <certificates src="system"/>\n      <certificates src="user"/>\n    </trust-anchors>\n  </base-config>\n'),
         NS('  <debug-overrides>\n    <trust-anchors>\n      <certificates src="user"/>\n    </trust-anchors>\n  </debug-overrides>\n'),
         "Release builds trust any CA the user (or malware, or an MDM profile) installs, which allows TLS interception. Trust user CAs only inside <debug-overrides>.",
         files=NSC_FILES, cwe=["CWE-295"], docv="Android network security configuration")

# ------------------------------------------------------------------ Kotlin code
CALL = lambda names: (f'((call_expression [(identifier) @m (navigation_expression (_) (identifier) @m .)]) @match (#match? @m "^({names})$"))')
sec("WEBVIEW-JS-BRIDGE", "WebView JavaScript bridge (addJavascriptInterface)", RISK + "insecure-webview-native-bridges",
    "there is no mechanism for the application to verify the origin of the calling frame within the WebView",
    CALL("addJavascriptInterface"), 'webView.addJavascriptInterface(WalletBridge(wallet), "wallet")\n', 'webView.evaluateJavascript("render()", null)\n',
    "Every frame loaded in this WebView, including third-party iframes and anything injected into a page, can call the bridge's @JavascriptInterface methods. Load only your own content, or use WebViewCompat.addWebMessageListener with an origin allow-list.",
    mode="ai-confirm", ai="Can this WebView load content not fully controlled by the app (remote URLs, iframes, user content), and do the exposed methods do anything sensitive?",
    cwe=["CWE-749"], docv="Android security risks")
sec("WEBVIEW-FILE-ACCESS", "WebView file access from web content enabled", WS, "Don't enable this setting if you open files that may be created or altered by external sources",
    '((assignment left: (navigation_expression (_) (identifier) @p .) right: (identifier) @v) @match (#match? @p "^(allowFileAccess|allowFileAccessFromFileURLs|allowUniversalAccessFromFileURLs)$") (#eq? @v "true"))\n'
    '((call_expression (navigation_expression (_) (identifier) @m .) (value_arguments . (value_argument (identifier) @v) .)) @match (#match? @m "^(setAllowFileAccess|setAllowFileAccessFromFileURLs|setAllowUniversalAccessFromFileURLs)$") (#eq? @v "true"))',
    "webView.settings.allowUniversalAccessFromFileURLs = true\n", "webView.settings.allowFileAccess = false\n",
    "Pages loaded from file:// (or any page, for universal access) can read local files, including the app's private data. Serve local content through WebViewAssetLoader over https://appassets.androidplatform.net instead.",
    cwe=["CWE-200"], docv="Android API 36")
sec("WORLD-ACCESSIBLE-MODE", "MODE_WORLD_READABLE / MODE_WORLD_WRITEABLE", CTX, "Creating world-readable files is very dangerous",
    '((identifier) @match (#match? @match "^MODE_WORLD_(READABLE|WRITEABLE)$"))',
    'val prefs = context.getSharedPreferences("session", Context.MODE_WORLD_READABLE)\n', 'val prefs = context.getSharedPreferences("session", Context.MODE_PRIVATE)\n',
    "Other apps could read (or overwrite) the file. Since Android 7 the call throws SecurityException. Use MODE_PRIVATE and share data through a FileProvider or content provider with permissions.",
    sev="critical", cwe=["CWE-732"], docv="Android API 36")
sec("FILE-WORLD-PERMISSION", "File made readable/writable by every app (ownerOnly = false)", "https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/io/File.html",
    "the read permission applies only to the owner's read permission; otherwise, it applies to everybody",
    '((call_expression (navigation_expression (_) (identifier) @m .) (value_arguments . (value_argument (identifier) @a) . (value_argument (identifier) @o) .)) @match (#match? @m "^(setReadable|setWritable|setExecutable)$") (#eq? @a "true") (#eq? @o "false"))',
    "File(context.filesDir, \"token\").setReadable(true, false)\n", "File(context.filesDir, \"token\").setReadable(true, true)\n",
    "ownerOnly=false grants the permission to every user/app on the device. Keep files private (ownerOnly = true) and share them through a FileProvider.",
    cwe=["CWE-732"], docv="Java SE 21 API", lang="kotlin")
sec("LOG-SENSITIVE", "Credential or token written to the device log", RISK + "log-info-disclosure", "apps print sensitive data into the device log",
    '((call_expression (navigation_expression (identifier) @c (identifier) @m .) (value_arguments (value_argument) (value_argument) @arg)) @match (#eq? @c "Log") (#match? @m "^(v|d|i|w|e|wtf|println)$") (#match? @arg "(?i)(password|passwd|secret|token|api_?key|authorization|bearer|credential|ssn|card_?number|cvv)"))',
    'Log.d(TAG, "login ok, token=$authToken")\n', 'Log.d(TAG, "login ok for user ${user.id}")\n',
    "Log output can be read by tools with READ_LOGS, bug-report captures and crash collectors. Do not log secrets or personal data; strip such logs from release builds.",
    mode="ai-confirm", ai="Does the logged value contain a real secret or personal data (not just a word like 'token' in a constant message), and is this log reachable in release builds?",
    cwe=["CWE-532"], docv="Android security risks")
sec("PREFS-PLAINTEXT-SECRET", "Secret stored in plain SharedPreferences", "https://mas.owasp.org/MASTG/tests/android/MASVS-STORAGE/MASTG-TEST-0287/", "SharedPreferences",
    '((call_expression (navigation_expression (_) (identifier) @m .) (value_arguments . (value_argument (string_literal) @k))) @match (#match? @m "^(putString|putStringSet)$") (#match? @k "(?i)(password|passwd|secret|token|api_?key|pin|private_?key|session)"))',
    'prefs.edit().putString("auth_token", token).apply()\n', 'prefs.edit().putString("theme", "dark").apply()\n',
    "SharedPreferences are an unencrypted XML file in the app sandbox; backups, rooted devices and file-access bugs expose it. Keep secrets in the Android Keystore (or encrypt them with a Keystore-held key) instead.",
    mode="ai-confirm", ai="Is the stored value a real credential/token/key (not a flag or a non-secret identifier), and is it stored without encryption?",
    cwe=["CWE-312"], docv="OWASP MASTG", filters=["file.lacks_re:EncryptedSharedPreferences|MasterKey|Cipher\\.getInstance"])
sec("BIOMETRIC-NO-CRYPTO", "BiometricPrompt.authenticate without a CryptoObject", "https://developer.android.com/identity/sign-in/biometric-auth",
    "incorporate cryptography into your biometric authentication workflow using an instance of CryptoObject",
    '((call_expression (navigation_expression (_) (identifier) @m .) (value_arguments . (value_argument) .)) @match (#eq? @m "authenticate"))',
    "val biometricPrompt = BiometricPrompt(this, executor, callback)\nbiometricPrompt.authenticate(promptInfo)\n", "val biometricPrompt = BiometricPrompt(this, executor, callback)\nbiometricPrompt.authenticate(promptInfo, BiometricPrompt.CryptoObject(cipher))\n",
    "Without a CryptoObject the result is only a callback the app trusts; on a compromised device it can be triggered without a biometric match. Bind the unlock to a Keystore key that requires user authentication.",
    mode="ai-confirm", ai="Does a successful callback here unlock something sensitive (keys, payments, account access) rather than just a convenience gate?",
    cwe=["CWE-287"], docv="Android developer guide", filters=["file.has_re:BiometricPrompt"])
sec("CLEARTEXT-URL", "HTTP (cleartext) URL used for a network request", RISK + "cleartext-communications",
    "anyone monitoring network traffic can see and manipulate the data that is being transmitted",
    '((call_expression [(identifier) @m (navigation_expression (_) (identifier) @m .)] (value_arguments . (value_argument (string_literal) @u))) @match (#match? @m "^(URL|url|baseUrl|get|post|newCall|openConnection|loadUrl)$") (#match? @u "^\\"http://"))',
    'val conn = URL("http://api.example.com/v1/login").openConnection()\n', 'val conn = URL("https://api.example.com/v1/login").openConnection()\n',
    "The request goes over plain HTTP, so anyone on the network path can read or change it. Use HTTPS.",
    sev="major", cwe=["CWE-319"], docv="Android security risks",
    filters=["node.lacks_re:http://(localhost|127\\.0\\.0\\.1|10\\.0\\.2\\.2|0\\.0\\.0\\.0|\\[::1\\])"])

# ------------------------------------------------------------------ release build hardening (M7)
sec("RELEASE-NO-MINIFY", "Release build type without R8 optimisation", "https://developer.android.com/build/shrink-code",
    "You should always enable optimization for your app's release build",
    '((call_expression (identifier) @r (annotated_lambda (lambda_literal (assignment left: (identifier) @l right: (identifier) @v) @match))) (#eq? @r "release") (#eq? @l "isMinifyEnabled") (#eq? @v "false"))',
    'android {\n    buildTypes {\n        release {\n            isMinifyEnabled = false\n        }\n    }\n}\n',
    'android {\n    buildTypes {\n        release {\n            isMinifyEnabled = true\n            isShrinkResources = true\n        }\n    }\n}\n',
    "The release APK ships unshrunk and unobfuscated bytecode, which makes reverse engineering, repackaging and finding secrets trivial. Enable R8 (isMinifyEnabled = true) for release.",
    sev="minor", files=KTS, cwe=["CWE-656"], docv="Android build guide",
)

# ------------------------------------------------------------------ MASVS-PLATFORM-3 FLAG_SECURE / MASVS-CODE-1 minSdk
FLAG = "https://developer.android.com/reference/android/view/WindowManager.LayoutParams#FLAG_SECURE"
sec("CLEAR-FLAG-SECURE", "window.clearFlags(FLAG_SECURE)", FLAG,
    "preventing it from appearing in screenshots",
    '((call_expression (navigation_expression (_) (identifier) @m .) (value_arguments (value_argument (navigation_expression (_) (identifier) @f .)))) @match (#eq? @m "clearFlags") (#eq? @f "FLAG_SECURE"))',
    "window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)\n",
    "window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)\n",
    "clearFlags(FLAG_SECURE) lets the window appear in screenshots, recent-apps thumbnails and on non-secure displays (screen recording, screen sharing). Keep FLAG_SECURE on screens that show secrets or personal data.",
    sev="major", cwe=["CWE-200"], owasp=["MASVS-PLATFORM-3", "M6:2024"], docv="Android API 36")
sec("PASSWORD-NO-FLAG-SECURE", "Password field without FLAG_SECURE on the window", FLAG,
    "preventing it from appearing in screenshots",
    '((assignment left: (navigation_expression (_) (identifier) @p .) right: (navigation_expression (_) (identifier) @v .)) @match (#eq? @p "inputType") (#match? @v "PASSWORD"))',
    'edit.inputType = InputType.TYPE_TEXT_VARIATION_PASSWORD\n',
    'window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)\nedit.inputType = InputType.TYPE_TEXT_VARIATION_PASSWORD\n',
    "A password (or PIN) field is shown without FLAG_SECURE, so the value can appear in screenshots, recents and screen recordings. Call window.addFlags(WindowManager.LayoutParams.FLAG_SECURE) on this Activity.",
    mode="ai-confirm", ai="Does this screen show a password, PIN or other secret, and is FLAG_SECURE not set on the window (including in a base Activity)?",
    cwe=["CWE-200"], owasp=["MASVS-PLATFORM-3", "M6:2024"], docv="Android API 36",
    filters=["file.lacks_re:FLAG_SECURE"])
SDK = "https://developer.android.com/privacy-and-security/security-config"
SDK_Q = "Android 9 (API level 28)"
SDK_MSG = "minSdk below 24 (Android 7) keeps the app installable on releases that lack network-security config, the file-URI ban and modern permission defaults. Raise minSdk (or minSdkVersion) to 24 or higher unless you still have a documented need to support those devices."
SDK_RX = r"^(1[0-9]|2[0-3])$"
manifest("LOW-MIN-SDK", "uses-sdk minSdkVersion below 24", SDK, SDK_Q,
         {"key": "manifest.uses-sdk.@minSdkVersion", "op": "matches", "value": SDK_RX},
         '<?xml version="1.0" encoding="utf-8"?>\n<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n  <uses-sdk android:minSdkVersion="21"/>\n  <application android:label="@string/app_name"/>\n</manifest>\n',
         '<?xml version="1.0" encoding="utf-8"?>\n<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n  <uses-sdk android:minSdkVersion="24"/>\n  <application android:label="@string/app_name"/>\n</manifest>\n',
         SDK_MSG, sev="minor", cwe=["CWE-16"], owasp=["MASVS-CODE-1", "M8:2024"], docv="Android network security configuration")
sec("LOW-MIN-SDK-KTS", "minSdk / minSdkVersion below 24 (Kotlin DSL)", SDK, SDK_Q,
    f'((assignment left: (identifier) @n right: (number_literal) @v) @match (#match? @n "^(minSdk|minSdkVersion)$") (#match? @v "{SDK_RX}"))',
    'android {\n    defaultConfig {\n        minSdk = 21\n    }\n}\n',
    'android {\n    defaultConfig {\n        minSdk = 24\n    }\n}\n',
    SDK_MSG, sev="minor", files=KTS, cwe=["CWE-16"], owasp=["MASVS-CODE-1", "M8:2024"], docv="Android network security configuration")
sec("LOW-MIN-SDK-GROOVY", "minSdk / minSdkVersion below 24 (Groovy DSL)", SDK, SDK_Q,
    f'((juxt_function_call name: (identifier) @n args: (argument_list (decimal_integer_literal) @v)) @match (#match? @n "^(minSdk|minSdkVersion)$") (#match? @v "{SDK_RX}"))\n'
    f'((assignment_expression left: (identifier) @n right: (decimal_integer_literal) @v) @match (#match? @n "^(minSdk|minSdkVersion)$") (#match? @v "{SDK_RX}"))',
    "android {\n    defaultConfig {\n        minSdkVersion 21\n    }\n}\n",
    "android {\n    defaultConfig {\n        minSdkVersion 24\n    }\n}\n",
    SDK_MSG, sev="minor", lang="groovy", files=GROOVY, cwe=["CWE-16"], owasp=["MASVS-CODE-1", "M8:2024"], docv="Android network security configuration")

RULES = P.R
