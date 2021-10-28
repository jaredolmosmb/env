from django.urls import path
from . import views

urlpatterns = [
	path('', views.apiOverview, name =  "api-overview"),
	path('procesarSNOMED/Bundle', views.ProcesarBundleView, name =  "api-procesarBundleSNOMED"),
	path('procesarSNOMED/DiagnosticReport', views.ProcesarDiagnosticReportView, name =  "api-procesarDiagnosticReportSNOMED"),
	]