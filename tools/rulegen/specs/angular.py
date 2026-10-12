"""Angular pack (framework layer on the TypeScript pack). TS rules use language `typescript`; external templates use the
`html` grammar (tree-sitter-html; control-flow blocks are text); inline `template:` strings are matched in TS.
Version dimension `angular` (@angular/core). Sources: Angular CHANGELOG (official deprecation/breaking-change log),
angular.dev guides and style guide."""
from specs._common import Pack

A = "https://angular.dev/"
CL = "https://raw.githubusercontent.com/angular/angular/main/CHANGELOG.md"
P = Pack("NG", "typescript", "Angular 22 (angular.dev)", {"angular": "*"}, framework="angular")


def imp(src, names):
    return (f'((import_statement (import_clause (named_imports (import_specifier name: (identifier) @n))) source: (string (string_fragment) @s)) @match '
            f'(#match? @s "^({src})$") (#match? @n "^({names})$"))')


def src(s):
    return f'((import_statement source: (string (string_fragment) @s)) @match (#match? @s "^({s})$"))'


def mcall(obj, prop):
    return (f'((call_expression function: (member_expression object: (_) @o property: (property_identifier) @p)) @match '
            f'(#match? @o "{obj}") (#match? @p "^({prop})$"))')


def ident_call(fn):
    return f'((call_expression function: (identifier) @f) @match (#match? @f "^({fn})$"))'


def deco_key(decos, key, val=None):
    v = f' (#match? @v "{val}")' if val else ""
    return (f'((decorator (call_expression function: (identifier) @d arguments: (arguments (object (pair key: (property_identifier) @k value: (_) @v) @match)))) '
            f'(#match? @d "^({decos})$") (#match? @k "^({key})$"){v})')


def deco(name):
    return f'((decorator [(call_expression function: (identifier) @d) (identifier) @d]) @match (#match? @d "^({name})$"))'


def inline_tpl(rx):
    return f'((pair key: (property_identifier) @k value: (template_string) @v) @match (#eq? @k "template") (#match? @v "{rx}"))'


def html_attr(rx, val=None):
    if val:
        return f'((attribute (attribute_name) @n (quoted_attribute_value (attribute_value) @v)) @match (#match? @n "{rx}") (#match? @v "{val}"))'
    return f'((attribute (attribute_name) @n) @match (#match? @n "{rx}"))'


def lifecycle(id, title, needle, query, bad, good, msg, removed, deprecated=None, dep_needle=None, cat="compatibility", **kw):
    P(f"{id}-REMOVED", f"{title} (removed in v{removed})", CL, needle, query, bad, good, msg, sev="critical", kind="removal", cat=cat,
      applies={"angular": f">={removed}.0"}, docv=f"Angular {removed}", **kw)
    if deprecated:
        P(f"{id}-DEPRECATED", f"{title} (deprecated since v{deprecated})", CL, dep_needle or needle, query, bad, good,
          msg + f" Removed in v{removed} — migrate before upgrading.", sev="minor", kind="deprecation", cat=cat,
          applies={"angular": f">={deprecated}.0 <{removed}.0"}, docv=f"Angular {deprecated}", **kw)


def dep(id, title, needle, query, bad, good, msg, since, sev="minor", cat="compatibility", url=CL, **kw):
    P(id, f"{title} (deprecated since v{since})", url, needle, query, bad, good, msg, sev=sev, kind="deprecation", cat=cat,
      applies={"angular": f">={since}"}, docv=f"Angular {since}", **kw)


# ======================================================================== removals (CHANGELOG "Breaking Changes")
lifecycle("COMPONENT-FACTORY-RESOLVER", "ComponentFactoryResolver / ComponentFactory", "are no longer available. Pass the component class directly to APIs",
          imp("@angular/core", "ComponentFactoryResolver|ComponentFactory"),
          "import { ComponentFactoryResolver } from '@angular/core';\n", "import { ViewContainerRef } from '@angular/core';\n",
          "Pass the component class directly to ViewContainerRef.createComponent or use createComponent().", 22, 14,
          dep_needle="Passing component factory resolvers are no longer needed.")
lifecycle("CREATE-NG-MODULE-REF", "createNgModuleRef", "was removed, use `createNgModule` instead", imp("@angular/core", "createNgModuleRef"),
          "import { createNgModuleRef } from '@angular/core';\n", "import { createNgModule } from '@angular/core';\n", "Use createNgModule.", 22, 14,
          dep_needle="is deprecated in favor of newly added `createNgModule` one.")
lifecycle("CHECK-NO-CHANGES", "ChangeDetectorRef.checkNoChanges", "was removed. In tests use `fixture.detectChanges()` instead.",
          mcall("(cdr|changeDetector|changeDetectorRef|ref|cd)$", "checkNoChanges"),
          "this.cdr.checkNoChanges();\n", "fixture.detectChanges();\n", "Use fixture.detectChanges() in tests.", 22, 17,
          dep_needle="`ChangeDetectorRef.checkNoChanges` is deprecated.")
lifecycle("PROVIDE-ROUTES", "provideRoutes()", "has been removed. Use `provideRouter()` or `ROUTES` as multi token if necessary.",
          imp("@angular/router", "provideRoutes"), "import { provideRoutes } from '@angular/router';\n", "import { provideRouter } from '@angular/router';\n",
          "Use provideRouter() (or the ROUTES multi token).", 22)
lifecycle("HAMMERJS", "HammerJS integration", "Hammer.js integration has been removed. Use your own implementation.",
          imp("@angular/platform-browser", "HammerModule|HammerGestureConfig|HAMMER_GESTURE_CONFIG|HAMMER_LOADER"),
          "import { HammerModule } from '@angular/platform-browser';\n", "import { BrowserModule } from '@angular/platform-browser';\n",
          "Hammer.js support is gone; use pointer events or a gesture library directly.", 22, 20,
          dep_needle="HammerJS support is deprecated and will be removed in a future major version.")
lifecycle("ANGULARJS-LIB", "getAngularLib/setAngularLib", "have been removed use `getAngularJSGlobal`/`setAngularJSGlobal` instead.",
          imp("@angular/upgrade/static|@angular/upgrade", "getAngularLib|setAngularLib"),
          "import { getAngularLib } from '@angular/upgrade/static';\n", "import { getAngularJSGlobal } from '@angular/upgrade/static';\n",
          "Use getAngularJSGlobal/setAngularJSGlobal.", 22)
lifecycle("NG-MODULE-FACTORY", "NgModuleFactory", "NgModuleFactory has been removed, use NgModule instead.", imp("@angular/core", "NgModuleFactory"),
          "import { NgModuleFactory } from '@angular/core';\n", "import { NgModule } from '@angular/core';\n", "Use the NgModule class directly.", 21)
lifecycle("MODULE-ID", "@Component moduleId", "`moduleId` was removed from `Component` metadata.", deco_key("Component|Directive", "moduleId"),
          "@Component({ moduleId: module.id, selector: 'app-a', template: '' })\nexport class A {}\n",
          "@Component({ selector: 'app-a', template: '' })\nexport class A {}\n", "moduleId had no effect for years; delete it.", 21, 16,
          dep_needle="property is now\n  deprecated. It did not have any effect for multiple major versions")
lifecycle("INTERPOLATION-OPTION", "@Component interpolation option", "The `interpolation` option on Components has been removed.",
          deco_key("Component", "interpolation"), "@Component({ selector: 'app-a', interpolation: ['[[', ']]'], template: '' })\nexport class A {}\n",
          "@Component({ selector: 'app-a', template: '' })\nexport class A {}\n", "Only the default {{ }} delimiters are supported.", 21, 18,
          dep_needle="`@Component.interpolation` is deprecated.")
lifecycle("PLATFORM-BROWSER-APPLICATION-CONFIG", "ApplicationConfig from @angular/platform-browser",
          "The deprecated `ApplicationConfig` export from `@angular/platform-browser` has been removed.",
          imp("@angular/platform-browser", "ApplicationConfig"), "import { ApplicationConfig } from '@angular/platform-browser';\n",
          "import { ApplicationConfig } from '@angular/core';\n", "Import ApplicationConfig from @angular/core.", 21, 16,
          dep_needle="`ApplicationConfig` has moved, please import `ApplicationConfig` from `@angular/core` instead.")
lifecycle("UPGRADE-ADAPTER", "UpgradeAdapter", "`UpgradeAdapter` is no longer available.", imp("@angular/upgrade", "UpgradeAdapter"),
          "import { UpgradeAdapter } from '@angular/upgrade';\n", "import { UpgradeModule } from '@angular/upgrade/static';\n",
          "Use UpgradeModule from @angular/upgrade/static.", 21)
lifecycle("TESTBED-GET", "TestBed.get", "`TestBed.get` has been removed. Use `TestBed.inject` instead.", mcall("^TestBed$", "get"),
          "const svc = TestBed.get(UserService);\n", "const svc = TestBed.inject(UserService);\n", "Use TestBed.inject (typed).", 20, 14, cat="testing")
lifecycle("INJECT-FLAGS", "InjectFlags", "`InjectFlags` has been removed.", imp("@angular/core", "InjectFlags"),
          "import { InjectFlags } from '@angular/core';\nconst s = inject(Svc, InjectFlags.Optional);\n",
          "import { inject } from '@angular/core';\nconst s = inject(Svc, { optional: true });\n", "Pass an options object ({ optional, self, skipSelf, host }).",
          20, 14, dep_needle="The bit field signature of `inject()` has been deprecated, in favor of the")
lifecycle("AFTER-RENDER", "afterRender (renamed afterEveryRender)", "afterRender was renamed to afterEveryRender.", imp("@angular/core", "afterRender"),
          "import { afterRender } from '@angular/core';\n", "import { afterEveryRender } from '@angular/core';\n", "Use afterEveryRender (or afterNextRender).", 20)
lifecycle("FLUSH-EFFECTS", "TestBed.flushEffects", "the `TestBed.flushEffects()` was removed - use", mcall("^TestBed$", "flushEffects"),
          "TestBed.flushEffects();\n", "TestBed.tick();\n", "Use TestBed.tick().", 20, cat="testing")
lifecycle("EXPERIMENTAL-ZONELESS", "provideExperimentalZonelessChangeDetection", "renamed to `provideZonelessChangeDetection`",
          imp("@angular/core", "provideExperimentalZonelessChangeDetection"),
          "import { provideExperimentalZonelessChangeDetection } from '@angular/core';\n", "import { provideZonelessChangeDetection } from '@angular/core';\n",
          "Renamed to provideZonelessChangeDetection.", 20)
lifecycle("BROWSER-MODULE-WITH-SERVER-TRANSITION", "BrowserModule.withServerTransition",
          "The deprecated `BrowserModule.withServerTransition` method has been removed. Please use the `APP_ID` DI token",
          mcall("^BrowserModule$", "withServerTransition"), "imports: [BrowserModule.withServerTransition({ appId: 'app' })];\n",
          "providers: [{ provide: APP_ID, useValue: 'app' }];\n", "Provide APP_ID instead.", 19, 16,
          dep_needle="`BrowserModule.withServerTransition` has been deprecated. `APP_ID` should be used instead to set the application ID.")
lifecycle("ROUTER-ERROR-HANDLER", "Router.errorHandler", "The `Router.errorHandler` property has been removed.",
          r'((assignment_expression left: (member_expression property: (property_identifier) @p)) @match (#eq? @p "errorHandler"))',
          "import { Router } from '@angular/router';\nthis.router.errorHandler = (e) => log(e);\n", "provideRouter(routes, withNavigationErrorHandler((e) => log(e)));\n",
          "Use withNavigationErrorHandler.", 19, filters=[r"file.has_re:@angular/router"])
lifecycle("TESTING-ASYNC", "async() test helper", "`async` has been removed, use `waitForAsync` instead.", imp("@angular/core/testing", "async"),
          "import { async } from '@angular/core/testing';\n", "import { waitForAsync } from '@angular/core/testing';\n", "Use waitForAsync.", 18, cat="testing")
lifecycle("PLATFORM-BROWSER-TRANSFER-STATE", "TransferState/makeStateKey from @angular/platform-browser",
          "Deprecated `StateKey`, `TransferState` and `makeStateKey` have been removed from `@angular/platform-browser`",
          imp("@angular/platform-browser", "TransferState|makeStateKey|StateKey|BrowserTransferStateModule"),
          "import { TransferState } from '@angular/platform-browser';\n", "import { TransferState } from '@angular/core';\n",
          "Import from @angular/core.", 18, 16, dep_needle="exports have been moved from `@angular/platform-browser` to `@angular/core`.")
lifecycle("SERVER-TRANSFER-STATE-MODULE", "ServerTransferStateModule", "deprecated `ServerTransferStateModule` has been removed.",
          imp("@angular/platform-server", "ServerTransferStateModule"), "import { ServerTransferStateModule } from '@angular/platform-server';\n",
          "import { ServerModule } from '@angular/platform-server';\n", "TransferState works without this module.", 18)
lifecycle("PLATFORM-DYNAMIC-SERVER", "platformDynamicServer", "deprecated `platformDynamicServer` has been removed.",
          imp("@angular/platform-server", "platformDynamicServer"), "import { platformDynamicServer } from '@angular/platform-server';\n",
          "import { platformServer } from '@angular/platform-server';\n", "Import @angular/compiler and use platformServer.", 18)
lifecycle("SIGNAL-MUTATE", "WritableSignal.mutate", "The `mutate` method was removed from the `WritableSignal` interface",
          mcall(".", "mutate"), "items = signal<number[]>([]);\nthis.items.mutate((list) => list.push(item));\n", "this.items.update((list) => [...list, item]);\n",
          "Use update() with an immutable change.", 17, filters=[r"file.has_re:\bsignal\s*[<(]"])
lifecycle("ZONE-DIST-IMPORT", "zone.js/dist deep import", "Deep and legacy `dist/` imports like", src("zone\\.js/(dist|bundles)/.*"),
          "import 'zone.js/dist/zone';\n", "import 'zone.js';\n", "Import 'zone.js' / 'zone.js/testing'.", 17)
lifecycle("ENTRY-COMPONENTS", "entryComponents", "has been deleted from the `@NgModule` and `@Component` public APIs.",
          deco_key("NgModule|Component", "entryComponents"), "@NgModule({ declarations: [A], entryComponents: [A] })\nexport class M {}\n",
          "@NgModule({ declarations: [A] })\nexport class M {}\n", "No effect since Ivy; delete it.", 16)
lifecycle("REFLECTIVE-INJECTOR", "ReflectiveInjector", "The `ReflectiveInjector` and related symbols were removed.",
          imp("@angular/core", "ReflectiveInjector|ResolvedReflectiveProvider"), "import { ReflectiveInjector } from '@angular/core';\n",
          "import { Injector } from '@angular/core';\n", "Use Injector.create.", 16)
lifecycle("RENDER-MODULE-FACTORY", "renderModuleFactory", "`renderModuleFactory` has been removed. Use `renderModule` instead.",
          imp("@angular/platform-server", "renderModuleFactory"), "import { renderModuleFactory } from '@angular/platform-server';\n",
          "import { renderModule } from '@angular/platform-server';\n", "Use renderModule / renderApplication.", 16)

# ======================================================================== deprecations (CHANGELOG "Deprecations")
for d, name in [("NG-IF", "ngIf"), ("NG-FOR", "ngFor"), ("NG-SWITCH", "ngSwitch(Case|Default)?")]:
    nice = name.split("(")[0]
    dep(f"{d}-STRUCTURAL", f"*{nice} structural directive", "are deprecated. Use the control flow blocks instead",
        html_attr(f"^\\\\*{name}$"), f"<div *{nice}=\"items\">x</div>\n" if nice != "ngSwitch" else "<div [ngSwitch]=\"m\"><p *ngSwitchCase=\"'a'\">A</p></div>\n",
        {"ngIf": "@if (items) {\n  <div>x</div>\n}\n", "ngFor": "@for (item of items; track item.id) {\n  <div>{{ item.name }}</div>\n}\n",
         "ngSwitch": "@switch (m) {\n  @case ('a') { <p>A</p> }\n}\n"}[nice],
        f"Use the built-in control flow (`ng generate @angular/core:control-flow`).", 20, lang="html", cat="modernization",
        xref=[A + "guide/templates/control-flow"])
    dep(f"{d}-INLINE", f"*{nice} in inline template", "are deprecated. Use the control flow blocks instead",
        inline_tpl(f"\\\\*{name}="), "@Component({ selector: 'app-a', template: `<p *" + nice + "=\"x\">x</p>` })\nexport class A {}\n",
        "@Component({ selector: 'app-a', template: `@if (x) { <p>x</p> }` })\nexport class A {}\n",
        "Use @if/@for/@switch blocks.", 20, cat="modernization")
dep("COMMON-STRUCTURAL-IMPORTS", "Importing NgIf/NgFor/NgSwitch", "are deprecated. Use the control flow blocks instead",
    imp("@angular/common", "NgIf|NgFor|NgForOf|NgSwitch|NgSwitchCase|NgSwitchDefault"), "import { NgIf, NgFor } from '@angular/common';\n",
    "import { NgOptimizedImage } from '@angular/common';\n", "Drop the import once templates use control-flow blocks.", 20, cat="modernization")
dep("PLATFORM-BROWSER-DYNAMIC", "@angular/platform-browser-dynamic", "All entries of the `@angular/platform-browser-dynamic`",
    src("@angular/platform-browser-dynamic(/testing)?"), "import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';\n",
    "import { platformBrowser } from '@angular/platform-browser';\n", "Use @angular/platform-browser (and platformBrowserTesting).", 20)
dep("NG-REFLECT-ATTRIBUTES", "Reliance on ng-reflect-* attributes", "This commit deprecates `ng-reflect-*` attributes",
    r'((string (string_fragment) @s) @match (#match? @s "ng-reflect-"))', "const el = fixture.debugElement.query(By.css('[ng-reflect-value=\"a\"]'));\n",
    "const el = fixture.debugElement.query(By.directive(Value));\n", "Angular no longer emits ng-reflect-* by default; query by directive/data-testid.",
    20, cat="testing")
dep("ANIMATIONS-PACKAGE", "@angular/animations", "The @angular/animations package is deprecated as of v20.2",
    src("@angular/animations(/browser)?") + "\n" + imp("@angular/platform-browser/animations(/async)?", "provideAnimations|provideAnimationsAsync|BrowserAnimationsModule|provideNoopAnimations|NoopAnimationsModule"),
    "import { trigger, transition, animate } from '@angular/animations';\n", "// use animate.enter / animate.leave with CSS\n",
    "Migrate to native CSS with animate.enter/animate.leave.", "20.2", url=A + "guide/animations/migration", cat="modernization")
dep("GET-CURRENT-NAVIGATION", "Router.getCurrentNavigation", "The Router.getCurrentNavigation method is deprecated. Use the Router.currentNavigation signal instead.",
    mcall("router$", "getCurrentNavigation"), "const nav = this.router.getCurrentNavigation();\n", "const nav = this.router.currentNavigation();\n",
    "Read the currentNavigation signal.", "20.2")
dep("HTTP-CLIENT-MODULE", "HttpClientModule / HttpClientXsrfModule / HttpClientJsonpModule", "HttpClientModule and HttpClientXsrfModule are also deprecated.",
    imp("@angular/common/http", "HttpClientModule|HttpClientXsrfModule|HttpClientJsonpModule"),
    "import { HttpClientModule } from '@angular/common/http';\n", "import { provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';\n",
    "Use provideHttpClient(...features).", 18, url=A + "guide/http/setup")
dep("JSONP", "HttpClient.jsonp / withJsonpSupport", "JSONP is deprecated withJsonpSupport , HttpClientJsonpModule , and the .jsonp() method on HttpClient are deprecated because JSONP can cause cross-site scripting (XSS) vulnerabi",
    mcall("http$", "jsonp") + "\n" + imp("@angular/common/http", "withJsonpSupport|JsonpClientBackend|JsonpInterceptor"),
    "this.http.jsonp(url, 'callback');\n", "this.http.get(url);\n", "JSONP is an XSS risk; use CORS with normal requests.", "22.1", sev="major",
    url=A + "guide/http/setup", cat="security")
dep("WITH-FETCH", "withFetch()", "`withFetch` is now deprecated, it can be safely removed.", imp("@angular/common/http", "withFetch"),
    "import { provideHttpClient, withFetch } from '@angular/common/http';\nprovideHttpClient(withFetch());\n",
    "import { provideHttpClient } from '@angular/common/http';\nprovideHttpClient();\n", "fetch is the default backend; remove withFetch().", 22, sev="info")
dep("REPORT-PROGRESS", "reportProgress request option", "The `reportProgress` option is deprecated please use `reportUploadProgress`",
    r'((pair key: (property_identifier) @k) @match (#eq? @k "reportProgress"))', "import { HttpClient } from '@angular/common/http';\nthis.http.post(url, body, { reportProgress: true, observe: 'events' });\n",
    "this.http.post(url, body, { reportUploadProgress: true, observe: 'events' });\n", "Use reportUploadProgress / reportDownloadProgress.", 22,
    filters=[r"file.has_re:@angular/common/http|HttpClient"])
dep("STATUS-TEXT", "HttpResponseBase.statusText", "`HttpResponseBase.statusText` is deprecated",
    r'((member_expression property: (property_identifier) @p) @match (#eq? @p "statusText"))', "import { HttpErrorResponse } from '@angular/common/http';\nconsole.error(err.statusText);\n",
    "console.error(err.status);\n", "statusText is unreliable over HTTP/2; use status.", 21, filters=[r"file.has_re:@angular/common/http"])
dep("UPGRADE-VERSION", "VERSION from @angular/upgrade", "from `@angular/upgrade` is deprecated. Please use the entry from `@angular/upgrade/static` instead.",
    imp("@angular/upgrade", "VERSION"), "import { VERSION } from '@angular/upgrade';\n", "import { VERSION } from '@angular/upgrade/static';\n",
    "Import from @angular/upgrade/static.", "21.1", sev="info")
dep("LOCALE-DATA-FUNCTIONS", "getLocale* data functions", "`getLocaleCurrencyName`",
    imp("@angular/common", "getCurrencySymbol|getLocale[A-Z]\\\\w*"), "import { getLocaleDayNames } from '@angular/common';\n",
    "const days = new Intl.DateTimeFormat(locale, { weekday: 'long' });\n", "Use the Intl API instead.", 18, sev="info")
dep("ANIMATION-DRIVER-NOOP", "AnimationDriver.NOOP", "The `AnimationDriver.NOOP` symbol is deprecated, use `NoopAnimationDriver` instead.",
    r'((member_expression object: (identifier) @o property: (property_identifier) @p) @match (#eq? @o "AnimationDriver") (#eq? @p "NOOP"))',
    "const d = AnimationDriver.NOOP;\n", "const d = new NoopAnimationDriver();\n", "Use NoopAnimationDriver.", 17, sev="info")
dep("RUN-IN-CONTEXT", "EnvironmentInjector.runInContext", "`EnvironmentInjector.runInContext` is now deprecated, with",
    mcall("njector$", "runInContext"), "this.injector.runInContext(() => inject(Svc));\n", "runInInjectionContext(this.injector, () => inject(Svc));\n",
    "Use runInInjectionContext(injector, fn).", 16)
dep("CAN-LOAD", "CanLoad guard", "CanLoad guards in the Router are deprecated. Use CanMatch",
    r'((pair key: (property_identifier) @k) @match (#eq? @k "canLoad"))' + "\n" + r'((implements_clause (type_identifier) @t) @match (#eq? @t "CanLoad"))',
    "const routes = [{ path: 'admin', canLoad: [AdminGuard], loadChildren: () => import('./admin') }];\n",
    "const routes = [{ path: 'admin', canMatch: [adminGuard], loadChildren: () => import('./admin') }];\n", "Use canMatch.", "15.1")
dep("CLASS-GUARDS", "Class-based guards/resolvers", "Class and `InjectionToken` guards and resolvers are",
    r'((implements_clause (type_identifier) @t) @match (#match? @t "^(CanActivate|CanActivateChild|CanDeactivate|CanMatch|Resolve)$"))',
    "export class AuthGuard implements CanActivate {\n  canActivate() {\n    return true;\n  }\n}\n",
    "export const authGuard: CanActivateFn = () => inject(AuthService).isAuthenticated();\n",
    "Write guards/resolvers as functions using inject().", "15.2", sev="info", cat="modernization", xref=[A + "guide/routing/route-guards"])
dep("ROUTER-LINK-WITH-HREF", "RouterLinkWithHref", "The `RouterLinkWithHref` directive is deprecated, use the `RouterLink` directive instead.",
    imp("@angular/router", "RouterLinkWithHref"), "import { RouterLinkWithHref } from '@angular/router';\n", "import { RouterLink } from '@angular/router';\n",
    "Use RouterLink.", 15)
dep("DATE-PIPE-DEFAULT-TIMEZONE", "DATE_PIPE_DEFAULT_TIMEZONE", "token is now deprecated in favor", imp("@angular/common", "DATE_PIPE_DEFAULT_TIMEZONE"),
    "import { DATE_PIPE_DEFAULT_TIMEZONE } from '@angular/common';\n", "import { DATE_PIPE_DEFAULT_OPTIONS } from '@angular/common';\n",
    "Use DATE_PIPE_DEFAULT_OPTIONS with { timezone }.", 15)
dep("PROVIDED-IN-NGMODULE", "providedIn: SomeNgModule", "The ability to pass an `NgModule` to the `providedIn` option for",
    deco_key("Injectable", "providedIn", "^[A-Z]"), "@Injectable({ providedIn: UserModule })\nexport class UserService {}\n",
    "@Injectable({ providedIn: 'root' })\nexport class UserService {}\n", "Use providedIn: 'root' or list it in providers.", 15)
dep("NG-COMPONENT-OUTLET-FACTORY", "ngComponentOutletNgModuleFactory input", "input of the `NgComponentOutlet` directive is deprecated",
    html_attr("ngComponentOutletNgModuleFactory"), "<ng-container *ngComponentOutlet=\"c; ngModuleFactory: f\" [ngComponentOutletNgModuleFactory]=\"f\"></ng-container>\n",
    "<ng-container *ngComponentOutlet=\"c; ngModule: m\"></ng-container>\n", "Use the ngModule input.", 14, lang="html")
dep("INITIAL-VALUE-IS-DEFAULT", "FormControl initialValueIsDefault", "The `initialValueIsDefault` option has been deprecated and replaced with",
    r'((pair key: (property_identifier) @k) @match (#eq? @k "initialValueIsDefault"))', "const c = new FormControl('', { initialValueIsDefault: true });\n",
    "const c = new FormControl('', { nonNullable: true });\n", "Use nonNullable.", 14)

# ======================================================================== modernization / best practices (guides + style guide)
P("STANDALONE-TRUE-REDUNDANT", "standalone: true is the default", CL, "Angular directives, components and pipes are now standalone by default.",
  deco_key("Component|Directive|Pipe", "standalone", "^true$"), "@Component({ selector: 'app-a', standalone: true, template: '' })\nexport class A {}\n",
  "@Component({ selector: 'app-a', template: '' })\nexport class A {}\n", "Since v19 standalone is the default; remove the flag.", sev="info",
  kind="modernization", cat="maintainability", applies={"angular": ">=19.0"}, docv="Angular 19")
P("STANDALONE-FALSE", "standalone: false (NgModule-declared)", A + "guide/ngmodules/overview",
  "The Angular team recommends using standalone components instead of NgModule for all new code.", deco_key("Component|Directive|Pipe", "standalone", "^false$"),
  "@Component({ selector: 'app-a', standalone: false, template: '' })\nexport class A {}\n", "@Component({ selector: 'app-a', template: '' })\nexport class A {}\n",
  "Migrate with `ng generate @angular/core:standalone`.", sev="info", kind="modernization", cat="modernization", applies={"angular": ">=19.0"})
P("NGMODULE-NEW-CODE", "@NgModule in new code", A + "guide/ngmodules/overview", "The Angular team recommends using standalone components instead of NgModule for all new code.",
  deco("NgModule"), "@NgModule({ declarations: [A], imports: [CommonModule] })\nexport class FeatureModule {}\n",
  "@Component({ selector: 'app-a', imports: [], template: '' })\nexport class A {}\n", "Prefer standalone components/providers functions.", sev="info",
  kind="modernization", cat="modernization", applies={"angular": ">=15.0"}, mode="ai-confirm", ai="Is this NgModule new or actively changing code (not a library compat shim)?")
P("BOOTSTRAP-MODULE", "bootstrapModule instead of bootstrapApplication", A + "guide/ngmodules/overview",
  "The Angular team recommends using bootstrapApplication instead of bootstrapModule for all new code.", mcall(".", "bootstrapModule"),
  "platformBrowserDynamic().bootstrapModule(AppModule);\n", "bootstrapApplication(App, appConfig);\n", "Bootstrap a standalone root component.",
  sev="info", kind="modernization", cat="modernization", applies={"angular": ">=15.0"})
P("INPUT-DECORATOR", "@Input() decorator (prefer input())", A + "guide/components/inputs",
  "While the Angular team recommends using the signal-based input function for new projects", deco("Input"),
  "export class Slider {\n  @Input() value = 0;\n}\n", "export class Slider {\n  readonly value = input(0);\n}\n",
  "Signal inputs are type-safe and work with computed/zoneless (`ng generate @angular/core:signal-input-migration`).", sev="info", kind="modernization",
  cat="modernization", applies={"angular": ">=17.1"})
P("OUTPUT-DECORATOR", "@Output() decorator (prefer output())", A + "guide/components/outputs",
  "While the Angular team recommends using the output function for new projects", deco("Output"),
  "export class Panel {\n  @Output() closed = new EventEmitter<void>();\n}\n", "export class Panel {\n  readonly closed = output<void>();\n}\n",
  "Use output() (`ng generate @angular/core:output-migration`).", sev="info", kind="modernization", cat="modernization", applies={"angular": ">=17.3"})
P("QUERY-DECORATOR", "@ViewChild/@ContentChild decorators (prefer signal queries)", A + "guide/components/queries",
  "While the Angular team recommends using the signal-based query function for new projects", deco("ViewChild|ViewChildren|ContentChild|ContentChildren"),
  "export class Form {\n  @ViewChild('name') name?: ElementRef;\n}\n", "export class Form {\n  readonly name = viewChild<ElementRef>('name');\n}\n",
  "Use viewChild()/contentChild() (`ng generate @angular/core:signal-queries-migration`).", sev="info", kind="modernization", cat="modernization",
  applies={"angular": ">=17.2"})
P("CONSTRUCTOR-INJECTION", "Constructor parameter injection (prefer inject())", A + "style-guide",
  "Prefer using the inject function over injecting constructor parameters.",
  r'((method_definition name: (property_identifier) @c parameters: (formal_parameters (required_parameter (accessibility_modifier))) @p) @match (#eq? @c "constructor"))',
  "@Component({ selector: 'app-a', template: '' })\nexport class A {\n  constructor(private http: HttpClient) {}\n}\n",
  "@Component({ selector: 'app-a', template: '' })\nexport class A {\n  private http = inject(HttpClient);\n}\n",
  "inject() has better type inference (`ng generate @angular/core:inject`).", sev="info", kind="modernization", cat="modernization",
  applies={"angular": ">=14.0"}, filters=[r"file.has_re:@(Component|Directive|Injectable|Pipe)\("])
P("HOST-DECORATORS", "@HostBinding/@HostListener (prefer host)", A + "guide/components/host-elements",
  "Always prefer using the host property over @HostBinding and @HostListener .", deco("HostBinding|HostListener"),
  "export class Slider {\n  @HostListener('keydown', ['$event'])\n  onKey(e: KeyboardEvent) {}\n}\n",
  "@Component({ selector: 'app-slider', host: { '(keydown)': 'onKey($event)' }, template: '' })\nexport class Slider {\n  onKey(e: KeyboardEvent) {}\n}\n",
  "These decorators exist for backwards compatibility; use the host metadata.", sev="info", kind="best-practice", cat="maintainability")
P("SERVICE-DECORATOR", "@Injectable({providedIn: 'root'}) (use @Service)", A + "guide/di",
  "The @Service decorator is an ergonomic shorthand for @Injectable({providedIn: 'root'})", deco_key("Injectable", "providedIn", "^.root.$"),
  "@Injectable({ providedIn: 'root' })\nexport class Api {}\n", "@Service()\nexport class Api {}\n", "Angular 22 adds @Service for root singletons.",
  sev="info", kind="modernization", cat="modernization", applies={"angular": ">=22.0"}, docv="Angular 22")
P("READONLY-SIGNAL-MEMBERS", "input()/output()/model()/queries not readonly", A + "style-guide",
  "Mark component and directive properties initialized by Angular as readonly .",
  r'((public_field_definition value: (call_expression function: [(identifier) @f (member_expression object: (identifier) @f)]) ) @match (#match? @f "^(input|output|model|viewChild|viewChildren|contentChild|contentChildren)$") (#not-match? @match "\\breadonly\\b"))',
  "export class Profile {\n  userId = input<string>();\n}\n", "export class Profile {\n  readonly userId = input<string>();\n}\n",
  "readonly prevents overwriting the signal Angular created.", sev="info", kind="best-practice", cat="maintainability", applies={"angular": ">=17.1"})
P("LIFECYCLE-INTERFACE", "Lifecycle hook without its interface", A + "style-guide",
  "When adding a lifecycle hook to your class, import and implement these interfaces to ensure that the methods ar",
  r'((class_declaration body: (class_body (method_definition name: (property_identifier) @m))) @match (#match? @m "^ng(OnInit|OnDestroy|OnChanges|DoCheck|AfterViewInit|AfterContentInit)$") (#not-match? @match "^[^{]*implements[^{]*(OnInit|OnDestroy|OnChanges|DoCheck|AfterViewInit|AfterContentInit)"))',
  "export class Profile {\n  ngOnInit() {}\n}\n", "export class Profile implements OnInit {\n  ngOnInit() {}\n}\n",
  "The interface catches misspelled hook names at compile time.", sev="info", kind="best-practice", cat="maintainability",
  quote="When adding a lifecycle hook to your class, import and implement these interfaces to ensure that the methods are named correctly.")
P("EXPENSIVE-CHECK-HOOKS", "ngDoCheck/ngAfter*Checked hook", A + "guide/components/lifecycle",
  "This method runs very frequently and can significantly impact your page's performance.",
  r'((method_definition name: (property_identifier) @m) @match (#match? @m "^ng(DoCheck|AfterViewChecked|AfterContentChecked)$"))',
  "export class A implements DoCheck {\n  ngDoCheck() {\n    this.recompute();\n  }\n}\n", "export class A {\n  readonly total = computed(() => sum(this.items()));\n}\n",
  "Runs on every change-detection pass; prefer signals/computed or OnPush.", sev="minor", kind="anti-pattern", cat="performance")
P("EFFECT-COPIES-SIGNAL", "effect() used to derive/copy state", A + "guide/signals/effect", "Effects should be the last API you reach for.",
  r'((call_expression function: (identifier) @f arguments: (arguments . (arrow_function body: (_) @b))) @match (#eq? @f "effect") (#match? @b "\\.set\\s*\\("))',
  "export class A {\n  copy = signal(0);\n  e = effect(() => {\n    this.copy.set(this.src() * 2);\n  });\n}\n",
  "export class A {\n  copy = computed(() => this.src() * 2);\n}\n", "Use computed()/linkedSignal() for derived values.", sev="minor", kind="anti-pattern",
  cat="correctness", applies={"angular": ">=16.0"}, mode="ai-confirm", ai="Is this effect only deriving state from other signals (no external side effect)?",
  quote="Effects should be the last API you reach for. Always prefer computed() for derived values and linkedSignal() for values that can be both derived and manually set.")
P("ALLOW-SIGNAL-WRITES", "effect allowSignalWrites (no-op since v19)", CL, "no-op `allowSignalWrites`",
  r'((pair key: (property_identifier) @k) @match (#eq? @k "allowSignalWrites"))', "effect(() => this.n.set(1), { allowSignalWrites: true });\n",
  "effect(() => this.n.set(1));\n", "The flag does nothing since v19; remove it.", sev="info", kind="deprecation", cat="maintainability",
  applies={"angular": ">=19.0"}, docv="Angular 19")
P("ZONE-STABILITY-OBSERVABLES", "NgZone.onMicrotaskEmpty/onStable/isStable", A + "guide/zoneless",
  "Applications and libraries need to remove uses of NgZone.onMicrotaskEmpty , NgZone.onUnstable , and NgZone.onS",
  r'((member_expression property: (property_identifier) @p) @match (#match? @p "^(onMicrotaskEmpty|onUnstable|onStable|isStable)$"))',
  "import { NgZone } from '@angular/core';\nthis.zone.onStable.subscribe(() => this.measure());\n", "afterNextRender(() => this.measure());\n",
  "These never fire in zoneless apps; use afterNextRender/afterEveryRender.", sev="minor", kind="migration", cat="compatibility",
  applies={"angular": ">=18.0"}, filters=[r"file.has_re:NgZone"])
P("ON-PUSH", "Component without OnPush change detection", A + "guide/zoneless",
  "The OnPush change detection strategy is not required, but it is a recommended step towards zoneless compatibility",
  r'((decorator (call_expression function: (identifier) @d arguments: (arguments (object) @o))) @match (#eq? @d "Component") (#not-match? @o "changeDetection"))',
  "@Component({ selector: 'app-a', template: '' })\nexport class A {}\n",
  "@Component({ selector: 'app-a', changeDetection: ChangeDetectionStrategy.OnPush, template: '' })\nexport class A {}\n",
  "OnPush reduces checks and prepares for zoneless (default from v22).", sev="info", kind="best-practice", cat="performance",
  applies={"angular": ">=2.0 <22.0"})
P("BYPASS-SECURITY-TRUST", "DomSanitizer.bypassSecurityTrust*", A + "best-practices/security",
  "Remember, whether a value is safe depends on context, s", mcall(".", "bypassSecurityTrust(Html|Script|Style|Url|ResourceUrl)"),
  "this.html = this.sanitizer.bypassSecurityTrustHtml(userInput);\n", "this.html = this.sanitizer.sanitize(SecurityContext.HTML, userInput);\n",
  "Disables Angular's XSS protection; only for constant/vetted values.", sev="major", kind="security", cat="security", mode="ai-confirm",
  ai="Can the value passed to bypassSecurityTrust* contain user/external input?")
P("NATIVE-ELEMENT-INNER-HTML", "Writing innerHTML via ElementRef", A + "best-practices/security",
  "Avoid directly interacting with the DOM and instead use Angular templates where possible.",
  r'((assignment_expression left: (member_expression object: (member_expression property: (property_identifier) @n) property: (property_identifier) @p)) @match (#eq? @n "nativeElement") (#match? @p "^(innerHTML|outerHTML)$"))',
  "this.el.nativeElement.innerHTML = this.comment;\n", "this.text.set(this.comment);\n",
  "Bypasses Angular sanitization (XSS); bind in the template or sanitize.", sev="major", kind="security", cat="security")
P("TEMPLATE-INNERHTML-BYPASS", "[innerHTML] bound to a trusted (bypassed) value", A + "best-practices/security",
  "Angular sanitizes untrusted values for HTML and URLs", html_attr("^\\\\[innerHTML\\\\]$"),
  "<div [innerHTML]=\"trustedHtml\"></div>\n", "<div>{{ text }}</div>\n", "Angular sanitizes [innerHTML], but not values marked trusted; verify the source.",
  sev="minor", kind="security", cat="security", lang="html", mode="ai-confirm", ai="Is the bound value produced by bypassSecurityTrustHtml or otherwise from untrusted input?")
P("NG-CLASS-STYLE", "ngClass/ngStyle (prefer class/style bindings)", A + "style-guide",
  "Prefer class and style bindings over using the NgClass and NgStyle directives.", html_attr("^\\\\[(ngClass|ngStyle)\\\\]$"),
  "<div [ngClass]=\"{ admin: isAdmin }\"></div>\n", "<div [class.admin]=\"isAdmin\"></div>\n", "Native bindings are simpler and faster.",
  sev="info", kind="best-practice", cat="maintainability", lang="html")
P("EVENT-HANDLER-NAMING", "Event handler named after the event", A + "style-guide",
  "Prefer naming event handlers for the action they perform rather than for the triggering event",
  html_attr("^\\\\((click|submit|change|keydown|keyup|input)\\\\)$", "^\\\\s*(on|handle)?(Click|Submit|Change|Keydown|Keyup|Input|click|submit)\\\\w*\\\\("),
  "<button (click)=\"handleClick()\">Save</button>\n", "<button (click)=\"saveUserData()\">Save</button>\n", "Name handlers for what they do.",
  sev="info", kind="best-practice", cat="maintainability", lang="html")
P("NG-FOR-TRACK-BY", "*ngFor without trackBy", A + "guide/templates/control-flow",
  "Using track effectively can significantly improve your application's rendering performance when looping over data collections.",
  r'((attribute (attribute_name) @n (quoted_attribute_value (attribute_value) @v)) @match (#eq? @n "*ngFor") (#not-match? @v "trackBy"))', "<li *ngFor=\"let u of users\">{{ u.name }}</li>\n",
  "@for (u of users; track u.id) {\n  <li>{{ u.name }}</li>\n}\n", "Without tracking, every change re-creates DOM nodes.", sev="minor", kind="anti-pattern",
  cat="performance", lang="html")
P("FOR-TRACK-INDEX-DYNAMIC", "@for tracking $index on dynamic data", A + "guide/templates/control-flow",
  "For static collections that never change, you can use $index to tell Angular to track each item by its index in the collection.",
  r'((text) @match (#match? @match "@for\\s*\\([^)]*track\\s+\\$index"))', "@for (u of users; track $index) {\n  <li>{{ u.name }}</li>\n}\n",
  "@for (u of users; track u.id) {\n  <li>{{ u.name }}</li>\n}\n", "Index tracking re-renders on insert/reorder; track a unique id.", sev="minor",
  kind="anti-pattern", cat="performance", lang="html", mode="ai-confirm", ai="Can this collection change order or have items inserted/removed?")
P("INPUT-ALIAS", "Aliased input/output", A + "guide/components/inputs", "While you should generally avoid aliasing inputs for components",
  r'((decorator (call_expression function: (identifier) @d arguments: (arguments (string)))) @match (#match? @d "^(Input|Output)$"))' + "\n"
  + r'((call_expression function: (identifier) @f arguments: (arguments (object (pair key: (property_identifier) @k)))) @match (#match? @f "^(input|output|model)$") (#eq? @k "alias"))',
  "export class Slider {\n  @Input('sliderValue') value = 0;\n}\n", "export class Slider {\n  readonly value = input(0);\n}\n",
  "Aliases make template and class names diverge.", sev="info", kind="best-practice", cat="maintainability")
P("INPUT-SETTER", "@Input setter (prefer transform/computed)", A + "guide/components/inputs",
  "Prefer using input transforms instead of getters and setters if possible.",
  r'((class_body (decorator (call_expression function: (identifier) @d)) . (method_definition "set") @match) (#eq? @d "Input"))',
  "export class Slider {\n  @Input() set value(v: number) {\n    this.internal = v;\n  }\n}\n",
  "export class Slider {\n  readonly value = input(0, { transform: numberAttribute });\n}\n",
  "Setters may run many times; use input transforms or computed().", sev="info", kind="best-practice", cat="performance")
P("DI-INTERCEPTOR", "Class-based HttpInterceptor", A + "guide/http/setup",
  "Functional interceptors (through withInterceptors ) have more predictable ordering and we recommend them over DI-based interceptors.",
  r'((implements_clause (type_identifier) @t) @match (#eq? @t "HttpInterceptor"))',
  "export class AuthInterceptor implements HttpInterceptor {\n  intercept(req: HttpRequest<unknown>, next: HttpHandler) {\n    return next.handle(req);\n  }\n}\n",
  "export const authInterceptor: HttpInterceptorFn = (req, next) => next(req);\n", "Use HttpInterceptorFn with withInterceptors().",
  sev="info", kind="modernization", cat="modernization", applies={"angular": ">=15.0"})
P("SUBSCRIBE-NO-TEARDOWN", "Component subscribe() without teardown", A + "ecosystem/rxjs-interop/take-until-destroyed",
  "The operator uses DestroyRef to know when the component or directive has been destroyed.",
  r'((class_declaration body: (class_body) @b) @match (#match? @b "\\.subscribe\\s*\\(") (#not-match? @b "takeUntilDestroyed|takeUntil|unsubscribe|DestroyRef|first\\(\\)|take\\(1\\)|toSignal"))',
  "@Component({ selector: 'app-a', template: '' })\nexport class A {\n  ngOnInit() {\n    this.store.changes.subscribe((v) => this.v = v);\n  }\n}\n",
  "@Component({ selector: 'app-a', template: '' })\nexport class A {\n  constructor() {\n    this.store.changes.pipe(takeUntilDestroyed()).subscribe((v) => this.v = v);\n  }\n}\n",
  "Long-lived subscriptions leak after destroy; use takeUntilDestroyed() or toSignal().", sev="minor", kind="anti-pattern", cat="correctness",
  applies={"angular": ">=16.0"}, filters=[r"file.has_re:@(Component|Directive)\("], mode="ai-confirm", ai="Is the observable long-lived (does not complete on its own, e.g. not a single HttpClient request)?")

RULES = P.R
