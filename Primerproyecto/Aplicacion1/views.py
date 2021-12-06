from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.template.loader import render_to_string 
from django.shortcuts import render
from .models import ConceptS, DescriptionS, Synonyms, ConceptosNoEncontrados, ExtendedmaprefsetS
from django.db.models import Q
from api.models import TokensDiagnosticos, TokensProcedures
from .servicios import generarRequest, normalize, validateJSON
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
import json
import copy
import nltk
import time
import es_core_news_sm
import spacy
from negspacy.negation import Negex


from .negex import *
import csv
# Create your views here.


#--------funcion para acomodar tokens por valor de indiece con valor a 1 (largo de palabras de la descrpicion)
def Sort(sub_li): 
	sub_li.sort(key = lambda x: x[1],reverse=True)
	return sub_li


#funicon para probar el procesamiento de distintos recursos de FHIR sin modificar la api
def InicioView(request):
	#pacientes = Paciente.objects.all()
	recurso = 'TokensDiagnosticos'

	if (recurso == 'TokensDiagnosticos'):
		with open("TextoLibreAdministracion.json", "r") as read_file:
			try:
				responseMA = json.load(read_file)
				responseMA1 = copy.deepcopy(responseMA)
				#print("valido")
				isValid = True
			except ValueError as err:
				#print("invalido")
				isValid = False
		if isValid:
			stop_words = set(stopwords.words("spanish"))
			descripciones = DescriptionS.objects.filter(category_id = 6)
			descAceptadas =[]

			start_time = time.time()
			concepto1 = ConceptS.objects.filter(active ="1") and ConceptS.objects.filter(category_id ="6")
			print("concepto1.coun", concepto1.count())

			for i in concepto1[0:0]:
				desc = DescriptionS.objects.filter(conceptid = i.id)
				for j in desc:
					#print(j.term)
					tokens = [t for t in j.term.split()]
					#tokens = word_tokenize(j.term)
					filt_tokens = [w.lower() for w in tokens if not w.lower() in stop_words]
					for k in filt_tokens:
						TokensDiagnosticos.objects.create(token=k.lower(), id_descripcion=j.id, largo_palabras_termino=len(filt_tokens))
						descAceptadas.append([k.lower(), j.id, len(filt_tokens)])



			#for j in range(1):
				#for i in descripciones[j*5000:(j+1)*5000-1]:
					#concepto = ConceptS.objects.get(id = i.conceptid)
					#if concepto.active == "1":
						#descAceptadas.append(i)
			print("len-descAceptadas", len(descAceptadas))
			#print("descAceptadas", descAceptadas)
			print("--- %s seconds ---" % (time.time() - start_time))

			data = "doc"

		else:
			responseMA ={"status": "json invalido"}
			responseMA1 = copy.deepcopy(responseMA)
			data=""
	return render(request, 'Aplicacion1/index.html')


