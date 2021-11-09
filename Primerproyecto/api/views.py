from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.template.loader import render_to_string 
from django.shortcuts import render
from rest_framework import status    
from Aplicacion1.models import ConceptS, DescriptionS, Synonyms, ConceptosNoEncontrados
from django.db.models import Q
from Aplicacion1.servicios import generarRequest, normalize, validateJSON
import json
import copy
from api.models import TokensDiagnosticos, TokensDiagnosticosFrecuentes, TokensProcedures
from Aplicacion1.servicios import generarRequest, normalize, validateJSON
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
import nltk
import time
import es_core_news_sm
import numpy
import spacy
import threading
from django.db import connections


def Sort(sub_li): 
	sub_li.sort(key = lambda x: x[1],reverse=True)
	return sub_li

def Sort_4(sub_li): 
	sub_li.sort(key = lambda x: x[4],reverse=True)
	return sub_li

def ProcesarOracion2(frasePrueba, indexP, val, start_time):
	# ---------TOKENIZAR POR PALABRAS LA FRASE A PROCESAR
	stop_words = set(stopwords.words("spanish"))
	#nlp = spacy.load('es_core_news_sm')  
	#doc=nlp(frasePrueba)
	#print([(w.text, w.pos_, w.dep_) for w in doc])
	#print("doc", doc)
	#sub_toks = [tok for tok in doc if (tok.dep_ == "nsubj") ]
	#print("sub_toks", sub_toks) 

	
	tokens_palabras = word_tokenize(frasePrueba)#tokenizo por palabras la frase del texto libre
	#print("--- %s seconds etapa 1 ---" % (time.time() - start_time))
	# ---------ELIMINAR STOPWORDS Y SUJETO DE ORACION
	#tokens_palabras = [w for w in tokens_palabras if not w in sub_toks]
	filt_frasePrueba = [w for w in tokens_palabras if not w in stop_words]# se quitan las stopwords de los tokens(palabras)
	#print("--- %s seconds etapa 2 ---" % (time.time() - start_time))


	# ---------GENERAR LISTA ANIDADA POR CADA TOKEN = [ID_DESCRIPCION, LARGO_PALABRAS]
	id_terminos_de_token=[]
	
	bd_tokens = TokensDiagnosticos.objects.raw("SELECT * FROM `api_tokensdiagnosticos` WHERE token IN %s", [tuple(filt_frasePrueba)])
	arfil = numpy.asarray(filt_frasePrueba)
	for indx, i in enumerate(arfil):#por cada token en la frase
		id_terminos_de_token.append([])
		for j in bd_tokens:#por cada token en la bd
			if j.token == i and j.largo_palabras_termino <=  len(filt_frasePrueba):#si token de frase esta en token de la instancia de la bd
				#id_terminos_de_token[indx].append([j.id_descripcion, j.largo_palabras_termino, j.token])#añado id de la descripcion que continee el token de la frase
				id_terminos_de_token[indx].append([int(j.id_descripcion), j.largo_palabras_termino])#añado id de la descripcion que continee el token de la frase
	max=0
	#print("--- %s seconds etapa 3 ---" % (time.time() - start_time))


	# ---------ELIMINAR DESCRIPCIONES QUE TENGAN MAS PALABRAS QUE LA DE LA FRASE A PROCESAR, ORDENAR CADA LISTA ANIDADA DE CADA TOKEN DE LARGO DE PALABRAS EN DESCRIPCION DE MANERA DESCENDENTE
	for term in id_terminos_de_token:
		Sort(term)	   
	#print("--- %s seconds etapa 4 ---" % (time.time() - start_time))

	# ---------IDENTIFICACIÓN DE DESCRIPCIONES QUE CONTENGAN AL TOKEN CON LA MISMA LONGITUD QU ELA FRASE PROCESADA
	termino_correcto=[]
	
	ar = numpy.asarray(id_terminos_de_token)
	ar2 = copy.deepcopy(ar)
	# id_terminos_de_token2 = copy.deepcopy(id_terminos_de_token)
	cont = 0
	contador = 1
	contador2 = 0
	for term in ar:
		for tupla in term:
			longitud_termino = tupla[1]
			id_desc=tupla[0]
			cont=1
			for term2 in ar2[contador:]:
				for tupla2 in term2:
					if tupla2[0] == id_desc:
						cont=cont+1
			if cont == longitud_termino:
				if tupla not in termino_correcto:
					termino_correcto.append(tupla)
		if contador != ar.size:
			contador = contador + 1

	#print("--- %s seconds etapa 5 ---" % (time.time() - start_time))


	# ---------ELIMINAR REPETIDOS GENERADOS EN EL PROCESO INMEDIATO ANTERIOR
	#termino_correcto2 = copy.deepcopy(termino_correcto)
	termino_correct_sin_repetido=[]
	for term in termino_correcto:
		if term[0] not in termino_correct_sin_repetido:
			termino_correct_sin_repetido.append(term[0])
	#print("--- %s seconds etapa 6 ---" % (time.time() - start_time))


	# ---------EXTRAER CONCEPTOS DE ACUARDO A LAS DESCRIPCIONES
	conceptos = []
	for term in termino_correct_sin_repetido:
		desc = DescriptionS.objects.filter(id =int(term))
		conceptos.append([desc[0].conceptid, ])
	data=""
	#print("--- %s seconds etapa 7 ---" % (time.time() - start_time))


	#---------VERIFICACION SI EL ORDEN DE PALABRAS EN LA DESCRIPCION Y FRASE ESTA TAL CUAL DE MANERA VCONSECUTIVA
	BooleanTalCual =[]
	descSeguncon =[]
	for conc in conceptos:
		esta=0
		descripciones = DescriptionS.objects.filter(conceptid = str(conc[0]))
		for descripcion in descripciones:
			if str(descripcion.term).lower() in str(frasePrueba).lower():
				esta=1
				indice_inicial = str(frasePrueba).lower().find(str(descripcion.term).lower())
				indice_final = indice_inicial + len(descripcion.term)
				descSeguncon.append([descripcion.term, conc[0], indice_inicial, indice_final, len(descripcion.term)])

		BooleanTalCual.append(esta)
	
	conceptos2 = []
	agregar=0
	for indexB, b in enumerate(BooleanTalCual):
		agregar = 0
		for indexC, c in enumerate(conceptos):
			if b == 1:
				agregar = 1
		if agregar == 1:
			#print("entre en agregar ", indexB)
			conceptos2.append(conceptos[indexB])
	#print("--- %s seconds etapa 8 ---" % (time.time() - start_time))


	# ---------ELIMINAR CONCEPTOS QUE ESTAN CONTENIDO EN CONCEPTOS CON UNA DESCRIPCION MAYOR
	conceptos3=[]
	Sort_4(descSeguncon)

	for elitem1 in descSeguncon[::-1]:
		for elitem2 in descSeguncon[::-1]:
			if elitem1 != elitem2:
				if elitem2[2] >=  elitem1[2] and elitem2[2] <= elitem1[3] and elitem2[3] > elitem1[2] and elitem2[3] <= elitem1[3]:
					#print("elitem2 = "+elitem2[0]+" esta en elitem1 = "+elitem1[0])
					if elitem2 in descSeguncon:
						descSeguncon.remove(elitem2)

	for itemotro in descSeguncon:
		conceptos3.append([itemotro[1]] )
	frasePrueba2=""

	aumento=0
	#print("--- %s seconds etapa 9 ---" % (time.time() - start_time))


	# ---------AÑADIR ENTRE GUIONES MEDIOS, LOS FSN DE LOS CONCEPTOS FINALES ENCONTRADOS
	conta = 0
	for indxconc3, conc3 in enumerate(conceptos3):
		descripciones = DescriptionS.objects.filter(conceptid = str(conc3[0]))
		for descripcion in descripciones:
			if str(descripcion.term).lower() in str(frasePrueba).lower():
				conta=conta+1
				if indxconc3 == 0:
					frasePrueba2 = copy.deepcopy(frasePrueba)
				indice_inicial = str(frasePrueba2).lower().find(str(descripcion.term).lower())
				#print("indice_inicial", indice_inicial)
				indice_final = indice_inicial + len(descripcion.term)
				FSN = DescriptionS.objects.get(conceptid = str(conc3[0]), typeid = "900000000000003001", active = "1")
				frasePrueba2 = frasePrueba2[:(indice_final)] + ' —'+FSN.term+'—' + frasePrueba2[(indice_final):]
	#print("--- %s seconds etapa 10 ---" % (time.time() - start_time))


	# ---------AÑADIR PROPIEDAD "EXTENSION" AL JSON PARA MOSTRAR CUANTOS CONCEPTOS SE ENCONTRARON Y SU ID		
	if "fullUrl" in val:		
		if len(conceptos3) >= 1:
			for item in conceptos3:
				if "extension" not in val['resource']:
					val['resource'].update( {"extension": [{
					"url" : "codeSNOMEDActivo "+str(indexP),
					"text" : item[0]
					}]} )
				else:
					val['resource']["extension"].append( {
					"url" : "codeSNOMEDActivo "+str(indexP),
					"text" : item[0]
					} )
	else:
		if len(conceptos3) >= 1:
			for item in conceptos3:
				if "extension" not in val:
					val.update( {"extension": [{
					"url" : "codeSNOMEDActivo "+str(indexP),
					"text" : item[0]
					}]} )
				else:
					val["extension"].append( {
					"url" : "codeSNOMEDActivo "+str(indexP),
					"text" : item[0]
					} )
	#-----------Guardar tokens de los conceptos encontrados en la frase
	descAceptadas=[]
	for i in conceptos3:
		desc = DescriptionS.objects.filter(conceptid = i[0])
		for j in desc:
			#print(j.term)
			tokens = [t for t in j.term.split()]
			#tokens = word_tokenize(j.term)
			filt_tokens = [w.lower() for w in tokens if not w.lower() in stop_words]
			for k in filt_tokens:
				p, created = TokensDiagnosticosFrecuentes.objects.get_or_create(
			    token=k.lower(),
			    id_descripcion=j.id,
			    largo_palabras_termino=len(filt_tokens))
				descAceptadas.append([k.lower(), j.id, len(filt_tokens)])
	#print("descAceptadas", descAceptadas)
	

	if frasePrueba2 == "":
		return frasePrueba
	else:
		return frasePrueba2
	
def ProcesarOracionFrecuentes(frasePrueba, indexP, val, start_time):
	# ---------TOKENIZAR POR PALABRAS LA FRASE A PROCESAR
	stop_words = set(stopwords.words("spanish"))
	#nlp = spacy.load('es_core_news_sm')  
	#doc=nlp(frasePrueba)
	#print([(w.text, w.pos_, w.dep_) for w in doc])
	#print("doc", doc)
	#sub_toks = [tok for tok in doc if (tok.dep_ == "nsubj") ]
	#print("sub_toks", sub_toks) 
	tokens_palabras = word_tokenize(frasePrueba)#tokenizo por palabras la frase del texto libre
	#print("--- %s seconds etapa 1 de bd frecuentes---" % (time.time() - start_time))
	# ---------ELIMINAR STOPWORDS Y SUJETOS (NSUBJ)
	#tokens_palabras = [w for w in tokens_palabras if not w in sub_toks]
	filt_frasePrueba = [w for w in tokens_palabras if not w in stop_words]# se quitan las stopwords de los tokens(palabras)
	#print("--- %s seconds etapa 2 bd frecuentes---" % (time.time() - start_time))


	# ---------GENERAR LISTA ANIDADA POR CADA TOKEN = [ID_DESCRIPCION, LARGO_PALABRAS]
	id_terminos_de_token=[]
	bd_tokens = TokensDiagnosticosFrecuentes.objects.raw("SELECT * FROM `api_tokensdiagnosticosfrecuentes` WHERE token IN %s", [tuple(filt_frasePrueba)])
	#bd_tokens = TokensDiagnosticos.objects.raw("SELECT * FROM `api_tokensdiagnosticos` WHERE token IN %s", [tuple(filt_frasePrueba)])
	arfil = numpy.asarray(filt_frasePrueba)
	for indx, i in enumerate(arfil):#por cada token en la frase
		id_terminos_de_token.append([])
		for j in bd_tokens:#por cada token en la bd
			if j.token == i and j.largo_palabras_termino <=  len(filt_frasePrueba):#si token de frase esta en token de la instancia de la bd
				#id_terminos_de_token[indx].append([j.id_descripcion, j.largo_palabras_termino, j.token])#añado id de la descripcion que continee el token de la frase
				id_terminos_de_token[indx].append([int(j.id_descripcion), j.largo_palabras_termino])#añado id de la descripcion que continee el token de la frase
	max=0
	#print("--- %s seconds etapa 3 bd frecuentes---" % (time.time() - start_time))


	# ---------ELIMINAR DESCRIPCIONES QUE TENGAN MAS PALABRAS QUE LA DE LA FRASE A PROCESAR, ORDENAR CADA LISTA ANIDADA DE CADA TOKEN DE LARGO DE PALABRAS EN DESCRIPCION DE MANERA DESCENDENTE
	for term in id_terminos_de_token:
		Sort(term)	   
	#print("--- %s seconds etapa 4 bd frecuentes---" % (time.time() - start_time))

	# ---------IDENTIFICACIÓN DE DESCRIPCIONES QUE CONTENGAN AL TOKEN CON LA MISMA LONGITUD QU ELA FRASE PROCESADA
	termino_correcto=[]
	
	ar = numpy.asarray(id_terminos_de_token)
	ar2 = copy.deepcopy(ar)
	# id_terminos_de_token2 = copy.deepcopy(id_terminos_de_token)
	contador = 1
	contador2 = 0
	cont=0
	for term in ar:
		for tupla in term:
			longitud_termino = tupla[1]
			id_desc=tupla[0]
			cont=1
			for term2 in ar2[contador:]:
				for tupla2 in term2:
					if tupla2[0] == id_desc:
						cont=cont+1
			if cont == longitud_termino:
				if tupla not in termino_correcto:
					termino_correcto.append(tupla)
		if contador != ar.size:
			contador = contador + 1

	#print("--- %s seconds etapa 5 bd frecuentes---" % (time.time() - start_time))


	# ---------ELIMINAR REPETIDOS GENERADOS EN EL PROCESO INMEDIATO ANTERIOR
	#termino_correcto2 = copy.deepcopy(termino_correcto)
	termino_correct_sin_repetido=[]
	for term in termino_correcto:
		if term[0] not in termino_correct_sin_repetido:
			termino_correct_sin_repetido.append(term[0])
	#print("--- %s seconds etapa 6 bd frecuentes ---" % (time.time() - start_time))


	# ---------EXTRAER CONCEPTOS DE ACUARDO A LAS DESCRIPCIONES
	conceptos = []
	for term in termino_correct_sin_repetido:
		desc = DescriptionS.objects.filter(id =int(term))
		conceptos.append([desc[0].conceptid, ])
	data=""
	#print("--- %s seconds etapa 7 bd frecuentes---" % (time.time() - start_time))


	#---------VERIFICACION SI EL ORDEN DE PALABRAS EN LA DESCRIPCION Y FRASE ESTA TAL CUAL DE MANERA VCONSECUTIVA
	BooleanTalCual =[]
	descSeguncon =[]
	for conc in conceptos:
		esta=0
		descripciones = DescriptionS.objects.filter(conceptid = str(conc[0]))
		for descripcion in descripciones:
			if str(descripcion.term).lower() in str(frasePrueba).lower():
				esta=1
				indice_inicial = str(frasePrueba).lower().find(str(descripcion.term).lower())
				indice_final = indice_inicial + len(descripcion.term)
				descSeguncon.append([descripcion.term, conc[0], indice_inicial, indice_final, len(descripcion.term)])

		BooleanTalCual.append(esta)
	
	conceptos2 = []
	agregar=0
	for indexB, b in enumerate(BooleanTalCual):
		agregar = 0
		for indexC, c in enumerate(conceptos):
			if b == 1:
				agregar = 1
		if agregar == 1:
			#print("entre en agregar ", indexB)
			conceptos2.append(conceptos[indexB])
	#print("--- %s seconds etapa 8 bd frecuentes---" % (time.time() - start_time))


	# ---------ELIMINAR COCNEPCTOS QUE ESTAN CONTENIDO EN CONCEPTOS CON UNA DESCRIPCION MAYOR
	conceptos3=[]
	Sort_4(descSeguncon)

	for elitem1 in descSeguncon[::-1]:
		for elitem2 in descSeguncon[::-1]:
			if elitem1 != elitem2:
				if elitem2[2] >=  elitem1[2] and elitem2[2] <= elitem1[3] and elitem2[3] > elitem1[2] and elitem2[3] <= elitem1[3]:
					#print("elitem2 = "+elitem2[0]+" esta en elitem1 = "+elitem1[0])
					if elitem2 in descSeguncon:
						descSeguncon.remove(elitem2)

	for itemotro in descSeguncon:
		conceptos3.append([itemotro[1]] )
	frasePrueba2=""

	aumento=0
	#print("--- %s seconds etapa 9 bd frecuentes---" % (time.time() - start_time))


	# ---------AÑADIR ENTRE GUIONES MEDIOS, LOS FSN DE LOS CONCEPTOS FINALES ENCONTRADOS
	conta = 0
	for indxconc3, conc3 in enumerate(conceptos3):
		descripciones = DescriptionS.objects.filter(conceptid = str(conc3[0]))
		for descripcion in descripciones:
			if str(descripcion.term).lower() in str(frasePrueba).lower():
				conta=conta+1
				if indxconc3 == 0:
					frasePrueba2 = copy.deepcopy(frasePrueba)
				indice_inicial = str(frasePrueba2).lower().find(str(descripcion.term).lower())
				#print("indice_inicial", indice_inicial)
				indice_final = indice_inicial + len(descripcion.term)
				FSN = DescriptionS.objects.get(conceptid = str(conc3[0]), typeid = "900000000000003001", active = "1")
				frasePrueba2 = frasePrueba2[:(indice_final)] + ' —'+FSN.term+'—' + frasePrueba2[(indice_final):]
	#print("--- %s seconds etapa 10 bd frecuentes---" % (time.time() - start_time))


	# ---------AÑADIR PROPIEDAD "EXTENSION" AL JSON PARA MOSTRAR CUANTOS CONCEPTOS SE ENCONTRARON Y SU ID		

	if "fullUrl" in val:		
		if len(conceptos3) >= 1:
			for item in conceptos3:
				if "extension" not in val['resource']:
					val['resource'].update( {"extension": [{
					"url" : "codeSNOMEDActivo "+str(indexP),
					"text" : item[0]
					}]} )
				else:
					val['resource']["extension"].append( {
					"url" : "codeSNOMEDActivo "+str(indexP),
					"text" : item[0]
					} )
	else:
		if len(conceptos3) >= 1:
			for item in conceptos3:
				if "extension" not in val:
					val.update( {"extension": [{
					"url" : "codeSNOMEDActivo "+str(indexP),
					"text" : item[0]
					}]} )
				else:
					val["extension"].append( {
					"url" : "codeSNOMEDActivo "+str(indexP),
					"text" : item[0]
					} )

	#-----------Guardar tokens de los conceptos encontrados en la frase
	"""descAceptadas=[]
	for i in conceptos3:
		desc = DescriptionS.objects.filter(conceptid = i[0])
		for j in desc:
			#print(j.term)
			tokens = [t for t in j.term.split()]
			#tokens = word_tokenize(j.term)
			filt_tokens = [w.lower() for w in tokens if not w.lower() in stop_words]
			for k in filt_tokens:
				TokensDiagnosticosFrecuentes.objects.create(token=k.lower(), id_descripcion=j.id, largo_palabras_termino=len(filt_tokens))
				descAceptadas.append([k.lower(), j.id, len(filt_tokens)])
	print("descAceptadas", descAceptadas)
	"""

	if frasePrueba2 == "":
		listaRetorno = [indexP, frasePrueba, 0]
		return listaRetorno
	else:
		listaRetorno = [indexP, frasePrueba2, 1]
		return listaRetorno

@api_view(['GET'])
def apiOverview(request):
	api_urls = {
		'ProcesarSNOMED Bundle': '/procesarSNOMED/Bundle',
		'ProcesarSNOMED DiagnosticReport': '/procesarSNOMED/DiagnosticReport',
		'ProcesarSNOMED Medication': '/procesarSNOMED/Medication',
		'ProcesarSNOMED MedicationAdministration': '/procesarSNOMED/MedicationAdministration',
		'ProcesarSNOMED Procedure': '/procesarSNOMED/Procedure',
		'ProcesarSNOMED Observation': '/procesarSNOMED/Observation',

	}
	return Response(api_urls)

@api_view(['POST'])
def ProcesarBundleView(request):
	responseMA = request.data
	print(responseMA)
	if (responseMA):
		recurso = responseMA['resourceType']
	#print("recurso = ", recurso)
	
	

		if (recurso == 'Bundle'):
		 start_time = time.time()
		 responseMA = request.data
		 responseMA1 = copy.deepcopy(responseMA)
		 for val in responseMA['entry']:
		 	if "Medication" == val['resource']['resourceType']:
		 		if 'code' in val['resource']:
		 			#data = normalize(val['resource']['code'].encode("latin-1").decode("utf-8"))
		 			data = normalize(val['resource']['code'])
			 		descripciones = DescriptionS.objects.filter(term = data) & DescriptionS.objects.filter(category_id = 10)
			 		sinonimos = Synonyms.objects.filter(term = data)
			 		if descripciones.count() > 1:
			 			for i in descripciones:
				 			con = ConceptS.objects.get(id = i.conceptid)
				 			if con.active == '0':
				 				descripciones = descripciones.exclude(id=i.id)
				 	if sinonimos.count() > 1:
			 			for i in sinonimos:
				 			con = ConceptS.objects.get(id = i.conceptid)
				 			if con.active == '0':
				 				sinonimos = sinonimos.exclude(id=i.id)
			 		if descripciones:
			 			concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
			 			if concepto.active == '1':
			 				val['resource'].update( {"extension": [{
			 					"url" : "codeSNOMEDActivo",
			 					"text" : descripciones[0].conceptid
			 					}]} ) 
			 			else:
			 				val['resource'].update( {"extension": [{
			 					"url" : "codeSNOMEDInactivo",
			 					"text" : descripciones[0].conceptid
			 					}]} ) 
			 		elif sinonimos:
			 			concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
			 			if concepto.active == '1':
			 				val['resource'].update( {"extension": [{
			 					"url" : "codeSNOMEDActivo",
			 					"text" : sinonimos[0].conceptid
			 					}]} ) 
			 			else:
			 				val['resource'].update( {"extension": [{
			 					"url" : "codeSNOMEDInactivo",
			 					"text" : sinonimos[0].conceptid
			 					}]} ) 
			 		else:
			 			val['resource'].update( {"extension": [{
			 					"url" : "codeSNOMED",
			 					"text" : 0
			 					}]} )
			 			existe = ConceptosNoEncontrados.objects.filter(concepto = data).first()
			 			if not existe:
			 				ConceptosNoEncontrados.objects.create(concepto = data)
			 	print("--- %s seconds Resource Medication ---" % (time.time() - start_time))

		 	if "MedicationAdministration" == val['resource']['resourceType']:
		 		if 'dosage' in val['resource']:
			 		if 'method' in val['resource']['dosage']:
				 		metodo = normalize(val['resource']['dosage']['method'])
		 				descripciones = DescriptionS.objects.filter(term = metodo) & DescriptionS.objects.filter(category_id = 8)
			 			sinonimos = Synonyms.objects.filter(term = metodo)
			 			if descripciones.count() > 1:
				 			for i in descripciones:
				 				con = ConceptS.objects.get(id = i.conceptid)
				 				if con.active == '0':
				 					descripciones = descripciones.exclude(id=i.id)
			 			if sinonimos.count() > 1:
			 	 			for i in sinonimos:
			 		 			con = ConceptS.objects.get(id = i.conceptid)
			 		 			if con.active == '0':
			 		 				sinonimos = sinonimos.exclude(id=i.id)
			 			if descripciones:
			 				concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
			 				if concepto.active == '1':
			 					val['resource'].update( {"extension": [{
			 					"url" : "methodSNOMEDActivo",
			 					"text" : descripciones[0].conceptid
			 					}]} ) 
			 				else:
			 					val['resource'].update( {"extension": [{
			 					"url" : "methodSNOMEDInactivo",
			 					"text" : descripciones[0].conceptid
			 					}]} ) 
			 			elif sinonimos:
			 				concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
			 				if concepto.active == '1':
			 					val['resource'].update( {"extension": [{
			 					"url" : "methodSNOMEDActivo",
			 					"text" : sinonimos[0].conceptid
			 					}]} ) 
			 				else:
			 					val['resource'].update( {"extension": [{
			 					"url" : "methodSNOMEDInactivo",
			 					"text" : sinonimos[0].conceptid
			 					}]} ) 
			 			else:
			 				val['resource'].update( {"extension": [{
			 					"url" : "methodSNOMEDInactivo",
			 					"text" : 0
			 					}]} ) 
			 				existe = ConceptosNoEncontrados.objects.filter(concepto = metodo).first()
				 			if not existe:
				 				print("entre en if not existe de administracion con metodo = "+ metodo)
				 				ConceptosNoEncontrados.objects.create(concepto = metodo)

			 	if 'dosage' in val['resource']:
			 		if 'route' in val['resource']['dosage']:
			 			#ruta = normalize(val['resource']['dosage']['route'].encode("latin-1").decode("utf-8"))
			 			ruta = normalize(val['resource']['dosage']['route'])
			 			descripciones = DescriptionS.objects.filter(term = ruta) & DescriptionS.objects.filter(category_id = 8)
			 			sinonimos = Synonyms.objects.filter(term = ruta)
			 			if descripciones.count() > 1:
				 			for i in descripciones:
				 				con = ConceptS.objects.get(id = i.conceptid)
				 				if con.active == '0':
				 					descripciones = descripciones.exclude(id=i.id)
			 			if sinonimos.count() > 1:
			 	 			for i in sinonimos:
			 		 			con = ConceptS.objects.get(id = i.conceptid)
			 		 			if con.active == '0':
			 		 				sinonimos = sinonimos.exclude(id=i.id)
			 			if descripciones:
			 				concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
			 				if concepto.active == '1':
			 					val['resource']['extension'].append({
			 					"url" : "rutaSNOMEDActivo",
			 					"text" : descripciones[0].conceptid
			 					} ) 
			 					print(val['resource']['extension'])
			 				else:
			 					val['resource']['extension'].append({
			 					"url" : "rutaSNOMEDInactivo",
			 					"text" : descripciones[0].conceptid
			 					} ) 
		 
		 				elif sinonimos:
		 					concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
		 					if concepto.active == '1':
		 						val['resource']['extension'].append({
			 					"url" : "rutaSNOMEDActivo",
			 					"text" : sinonimos[0].conceptid
			 					} ) 
		 					else:
		 						val['resource']['extension'].append({
			 					"url" : "rutaSNOMEDActivo",
			 					"text" : sinonimos[0].conceptid
			 					} ) 
		 				else:
		 					val['resource']['extension'].append({
			 					"url" : "rutaSNOMED",
			 					"text" : 0
			 					} ) 

		 					existe = ConceptosNoEncontrados.objects.filter(concepto = ruta).first()

				 			if not existe:
				 				ConceptosNoEncontrados.objects.create(concepto = ruta)
			 	print("--- %s seconds Resource MedicationAdministration ---" % (time.time() - start_time))
		 	if "DiagnosticReport" == val['resource']['resourceType']:
		 		if 'conclusionCode' in val['resource']:
			 		conclusionCode = normalize(val['resource']['conclusionCode'])
			 		descripciones = DescriptionS.objects.filter(term = conclusionCode) & DescriptionS.objects.filter(category_id = 6)
			 		sinonimos = Synonyms.objects.filter(term = conclusionCode)
			 		if descripciones.count() > 1:
			 			for i in descripciones:
				 			con = ConceptS.objects.get(id = i.conceptid)
				 			if con.active == '0':
				 				descripciones = descripciones.exclude(id=i.id)
				 	if sinonimos.count() > 1:
			 			for i in sinonimos:
				 			con = ConceptS.objects.get(id = i.conceptid)
				 			if con.active == '0':
				 				sinonimos = sinonimos.exclude(id=i.id)
			 		if descripciones:
			 			concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
			 			if concepto.active == '1':
			 				val['resource'].update( {"extension": [{
			 					"url" : "conclusionCodeSNOMEDActivo",
			 					"text" : descripciones[0].conceptid
			 					}]} ) 
			 			else:
			 				val['resource'].update( {"extension": [{
			 					"url" : "conclusionCodeSNOMEDInactivo",
			 					"text" : descripciones[0].conceptid
			 					}]} ) 
			 		elif sinonimos:
			 			concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
			 			if concepto.active == '1':
			 				val['resource'].update( {"extension": [{
			 					"url" : "conclusionCodeSNOMEDActivo",
			 					"text" : sinonimos[0].conceptid
			 					}]} ) 
			 			else:
			 				val['resource'].update( {"extension": [{
			 					"url" : "conclusionCodeSNOMEDInactivo",
			 					"text" : sinonimos[0].conceptid
			 					}]} ) 
			 		else:
			 			val['resource'].update( {"extension": [{
			 					"url" : "conclusionCodeSNOMED",
			 					"text" : 0
			 					}]} ) 
			 			existe = ConceptosNoEncontrados.objects.filter(concepto = conclusionCode).first()
			 			if not existe:
			 				ConceptosNoEncontrados.objects.create(concepto = conclusionCode)
			 	if 'conclusion' in val['resource']:
			 		frasePrueba = val['resource']['conclusion'].lower() 
			 		#frasePrueba = normalize(val['resource']['conclusion']).lower()
			 		stop_words = set(stopwords.words("spanish"))
			 		frasePrueba = frasePrueba.replace(',', '.')
			 		tokens_frases = sent_tokenize(frasePrueba)
			 		print("len(tokens_frases)", len(tokens_frases))
			 		fraseFinal = ""
			 		#----Procesamiento sin preprocesamiento de frases Frecuentes
			 		"""
			 		if tokens_frases:
			 			for indx, frases in enumerate(tokens_frases):
			 				if indx == 0:
			 					fraseFinal = fraseFinal + ProcesarOracion2(frases, indx, val, start_time).capitalize()
			 				else:
			 					fraseFinal = fraseFinal + " "+ ProcesarOracion2(frases, indx, val, start_time).capitalize()
			 				#ProcesarOracion2(frases, indx, val)
			 		"""
			 		status_frases = []
			 		if tokens_frases:
			 			for indx, frases in enumerate(tokens_frases):
			 				status_frases.append(ProcesarOracionFrecuentes(frases, indx, val, start_time))

			 				#ProcesarOracion2(frases, indx, val)
			 		for indx_status, frases_status in enumerate(status_frases):
			 			if indx_status == 0:
			 				if frases_status[2] == 1:
			 					fraseFinal = fraseFinal + frases_status[1].capitalize()
			 				if frases_status[2] == 0:
			 					fraseFinal = fraseFinal + ProcesarOracion2(frases_status[1], indx_status, val, start_time).capitalize()
			 			else:
			 				if frases_status[2] == 1:
			 					fraseFinal = fraseFinal + " "+ frases_status[1].capitalize()
			 				if frases_status[2] == 0:
			 					fraseFinal = fraseFinal + " "+ ProcesarOracion2(frases_status[1], indx_status, val, start_time).capitalize()



			 		val['resource'].update( {"conclusion": fraseFinal} )

			 	print("--- %s seconds Resource DiagnosticReport ---" % (time.time() - start_time))	

		 	if "Procedure" == val['resource']['resourceType']:
		 		if 'code' in val['resource']:
		 			procedimiento = normalize(val['resource']['code'])
		 			descripciones = DescriptionS.objects.filter(term = procedimiento) & DescriptionS.objects.filter(category_id = 4)
		 			sinonimos = Synonyms.objects.filter(term = procedimiento)
		 			if descripciones.count() > 1:
			 			for i in descripciones:
				 			con = ConceptS.objects.get(id = i.conceptid)
				 			if con.active == '0':
				 				descripciones = descripciones.exclude(id=i.id)
				 			#print(i.term, i.conceptid, con.active)
				 	if sinonimos.count() > 1:
			 			for i in sinonimos:
				 			con = ConceptS.objects.get(id = i.conceptid)
				 			if con.active == '0':
				 				sinonimos = sinonimos.exclude(id=i.id)
				 			#print(i.term, i.conceptid, con.active)
		 			if descripciones:
		 				concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
		 				if concepto.active == '1':
		 					val['resource'].update( {"extension": [{
		 					"url" : "codeSNOMEDActivo",
		 					"text" : descripciones[0].conceptid
		 					}]} ) 
		 				else:
		 					val['resource'].update( {"extension": [{
		 					"url" : "codeSNOMEDInactivo",
		 					"text" : descripciones[0].conceptid
		 					}]} )
		 			elif sinonimos:
		 				concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
		 				if concepto.active == "1":
		 					val['resource'].update( {"extension": [{
		 					"url" : "codeSNOMEDActivo",
		 					"text" : sinonimos[0].conceptid
		 					}]} )
 						else:
 							val['resource'].update( {"extension": [{
		 					"url" : "codeSNOMEDInactivo",
		 					"text" : sinonimos[0].conceptid
		 					}]} )
 					else:
 						val['resource'] .update( {"extension": [{
		 					"url" : "codeSNOMED",
		 					"text" : 0
		 					}]} )
 						existe = ConceptosNoEncontrados.objects.filter(concepto = procedimiento).first()
			 			if not existe:
			 				ConceptosNoEncontrados.objects.create(concepto = procedimiento)
			
		 		print("--- %s seconds Resource Procedure ---" % (time.time() - start_time))
			 			
		 	if "Observation" == val['resource']['resourceType']:
		 		if 'category' in val['resource']:
			 		#categoria = normalize(val['resource']['category'].encode("latin-1").decode("utf-8"))
			 		categoria = normalize(val['resource']['category'])
			 		descripciones = DescriptionS.objects.filter(term = categoria)
			 		sinonimos = Synonyms.objects.filter(term = categoria)
			 		if descripciones.count() > 1:
			 			for i in descripciones:
				 			con = ConceptS.objects.get(id = i.conceptid)
				 			if con.active == '0':
				 				descripciones = descripciones.exclude(id=i.id)
				 	if sinonimos.count() > 1:
			 			for i in sinonimos:
				 			con = ConceptS.objects.get(id = i.conceptid)
				 			if con.active == '0':
				 				sinonimos = sinonimos.exclude(id=i.id)
			 		if descripciones:
			 			concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
			 			if concepto.active == '1':
			 				val['resource'].update( {"extension": [{
			 					"url" : "categorySNOMEDActivo",
			 					"text" : descripciones[0].conceptid
			 					}]} ) 
			 			else:
			 				val['resource'].update( {"extension": [{
			 					"url" : "categorySNOMEDInactivo",
			 					"text" : descripciones[0].conceptid
			 					}]} )
			 		elif sinonimos:
			 			concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
			 			if concepto.active == '1':
			 				val['resource'].update( {"extension": [{
			 					"url" : "categorySNOMEDActivo",
			 					"text" : sinonimos[0].conceptid
			 					}]} ) 
			 			else:
			 				val['resource'].update( {"extension": [{
			 					"url" : "categorySNOMEDInactivo",
			 					"text" : sinonimos[0].conceptid
			 					}]} ) 

			 		else:
			 			val['resource'].update( {"extension": [{
			 					"url" : "categorySNOMED",
			 					"text" : 0
			 					}]} )
			 			existe = ConceptosNoEncontrados.objects.filter(concepto = categoria).first()
			 			if not existe:
			 				ConceptosNoEncontrados.objects.create(concepto = categoria)

		 		if 'code' in val['resource']:
			 		code = normalize(val['resource']['code'])
			 		descripciones = DescriptionS.objects.filter(term = code)
			 		sinonimos = Synonyms.objects.filter(term = code)
			 		if descripciones.count() > 1:
			 			for i in descripciones:
				 			con = ConceptS.objects.get(id = i.conceptid)
				 			if con.active == '0':
				 				descripciones = descripciones.exclude(id=i.id)
				 			#print(i.term, i.conceptid, con.active)
				 	if sinonimos.count() > 1:
			 			for i in sinonimos:
				 			con = ConceptS.objects.get(id = i.conceptid)
				 			if con.active == '0':
				 				sinonimos = sinonimos.exclude(id=i.id)
				 			#print(i.term, i.conceptid, con.active)
				 	if descripciones:
			 			concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
			 			if concepto.active == '1':
			 				val['resource']['extension'].append({
			 					"url" : "codeSNOMEDActivo",
			 					"text" : descripciones[0].conceptid
			 					} ) 
			 			else:
			 				val['resource']['extension'].append({
			 					"url" : "codeSNOMEDInactivo",
			 					"text" : descripciones[0].conceptid
			 					} ) 
			 		elif sinonimos:
			 			concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
			 			if concepto.active == '1':
			 				val['resource']['extension'].append({
			 					"url" : "codeSNOMEDActivo",
			 					"text" : sinonimos[0].conceptid
			 					} ) 
			 			else:
			 				val['resource']['extension'].append({
			 					"url" : "codeSNOMEDInactivo",
			 					"text" : sinonimos[0].conceptid
			 					} ) 
	 				else:
	 					val['resource']['extension'].append({
			 					"url" : "codeSNOMED",
			 					"text" : 0
			 					} ) 
	 					existe = ConceptosNoEncontrados.objects.filter(concepto = code).first()

			 			if not existe:
			 				ConceptosNoEncontrados.objects.create(concepto = code)
			 	print("--- %s seconds Resource Observation ---" % (time.time() - start_time))

		 data=""
		 print("--- %s seconds ---" % (time.time() - start_time))
		 return Response(responseMA)
	else:
		return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def ProcesarDiagnosticReportView(request):
	responseMA = request.data
	if (responseMA):
		recurso = responseMA['resourceType']
		if (recurso == 'DiagnosticReport'):
			start_time = time.time()
			if 'conclusionCode' in responseMA:
		 		conclusionCode = normalize(responseMA['conclusionCode'])
		 		print("conclusionCode", conclusionCode)
		 		descripciones = DescriptionS.objects.filter(term = conclusionCode) & DescriptionS.objects.filter(category_id = 6)
		 		sinonimos = Synonyms.objects.filter(term = conclusionCode)
		 		if descripciones.count() > 1:
		 			for i in descripciones:
			 			con = ConceptS.objects.get(id = i.conceptid)
			 			if con.active == '0':
			 				descripciones = descripciones.exclude(id=i.id)
			 	if sinonimos.count() > 1:
		 			for i in sinonimos:
			 			con = ConceptS.objects.get(id = i.conceptid)
			 			if con.active == '0':
			 				sinonimos = sinonimos.exclude(id=i.id)
		 		if descripciones:
		 			concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
		 			if concepto.active == '1':
		 				responseMA.update( {"extension": [{
		 					"url" : "conclusionCodeSNOMEDActivo",
		 					"text" : descripciones[0].conceptid
		 					}]} ) 
		 			else:
		 				responseMA.update( {"extension": [{
		 					"url" : "conclusionCodeSNOMEDInactivo",
		 					"text" : descripciones[0].conceptid
		 					}]} ) 
		 		elif sinonimos:
		 			concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
		 			if concepto.active == '1':
		 				responseMA.update( {"extension": [{
		 					"url" : "conclusionCodeSNOMEDActivo",
		 					"text" : sinonimos[0].conceptid
		 					}]} ) 
		 			else:
		 				responseMA.update( {"extension": [{
		 					"url" : "conclusionCodeSNOMEDInactivo",
		 					"text" : sinonimos[0].conceptid
		 					}]} ) 
		 		else:
		 			responseMA.update( {"extension": [{
		 					"url" : "conclusionCodeSNOMED",
		 					"text" : 0
		 					}]} ) 
		 			if conclusionCode != "":	 				
			 			existe = ConceptosNoEncontrados.objects.filter(concepto = conclusionCode).first()
			 			if not existe:
			 				ConceptosNoEncontrados.objects.create(concepto = conclusionCode)
			if 'conclusion' in responseMA:
		 		#frasePrueba = normalize(responseMA['conclusion']).lower()
		 		frasePrueba = responseMA['conclusion'].lower()
		 		stop_words = set(stopwords.words("spanish"))
		 		frasePrueba = frasePrueba.replace(',', '.')
		 		tokens_frases = sent_tokenize(frasePrueba)
		 		#print("len(tokens_frases)", len(tokens_frases))
		 		#print("tokens_frases", tokens_frases)
		 		fraseFinal = ""
		 		#----Procesamiento sin preprocesamiento de frases Frecuentes
		 		"""
		 		if tokens_frases:
		 			for indx, frases in enumerate(tokens_frases):
		 				if indx == 0:
		 					fraseFinal = fraseFinal + ProcesarOracion2(frases, indx, responseMA, start_time).capitalize()
		 				else:
		 					fraseFinal = fraseFinal + " "+ ProcesarOracion2(frases, indx, responseMA, start_time).capitalize()
		 				#ProcesarOracion2(frases, indx, responseMA)
		 		"""
		 		status_frases = []
		 		if tokens_frases:
		 			for indx, frases in enumerate(tokens_frases):
		 				status_frases.append(ProcesarOracionFrecuentes(frases, indx, responseMA, start_time))

		 				#ProcesarOracion2(frases, indx, responseMA)
		 		for indx_status, frases_status in enumerate(status_frases):
		 			if indx_status == 0:
		 				if frases_status[2] == 1:
		 					fraseFinal = fraseFinal + frases_status[1].capitalize()
		 				if frases_status[2] == 0:
		 					fraseFinal = fraseFinal + ProcesarOracion2(frases_status[1], indx_status, responseMA, start_time).capitalize()
		 			else:
		 				if frases_status[2] == 1:
		 					fraseFinal = fraseFinal + " "+ frases_status[1].capitalize()
		 				if frases_status[2] == 0:
		 					fraseFinal = fraseFinal + " "+ ProcesarOracion2(frases_status[1], indx_status, responseMA, start_time).capitalize()



		 		responseMA.update( {"conclusion": fraseFinal} )
			print("--- %s seconds Resource DiagnosticReport alone ---" % (time.time() - start_time))	
			return Response(responseMA)
	else:
		return Response(status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def ProcesarMedicationView(request):
	responseMA = request.data
	if (responseMA):
		recurso = responseMA['resourceType']
		if (recurso == 'Medication'):
			start_time = time.time()
			if 'code' in responseMA:
				#data = normalize(val['resource']['code'].encode("latin-1").decode("utf-8"))
				data = normalize(responseMA['code'])
			descripciones = DescriptionS.objects.filter(term = data) & DescriptionS.objects.filter(category_id = 10)
			sinonimos = Synonyms.objects.filter(term = data)
			if descripciones.count() > 1:
				for i in descripciones:
		 			con = ConceptS.objects.get(id = i.conceptid)
		 			if con.active == '0':
		 				descripciones = descripciones.exclude(id=i.id)
			if sinonimos.count() > 1:
	 			for i in sinonimos:
		 			con = ConceptS.objects.get(id = i.conceptid)
		 			if con.active == '0':
		 				sinonimos = sinonimos.exclude(id=i.id)
			if descripciones:
	 			concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
	 			if concepto.active == '1':
	 				responseMA.update( {"extension": [{
	 					"url" : "codeSNOMEDActivo",
	 					"text" : descripciones[0].conceptid
	 					}]} ) 
	 			else:
	 				responseMA.update( {"extension": [{
	 					"url" : "codeSNOMEDInactivo",
	 					"text" : descripciones[0].conceptid
	 					}]} ) 
			elif sinonimos:
	 			concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
	 			if concepto.active == '1':
	 				responseMA.update( {"extension": [{
	 					"url" : "codeSNOMEDActivo",
	 					"text" : sinonimos[0].conceptid
	 					}]} ) 
	 			else:
	 				responseMA.update( {"extension": [{
	 					"url" : "codeSNOMEDInactivo",
	 					"text" : sinonimos[0].conceptid
	 					}]} ) 
			else:
	 			responseMA.update( {"extension": [{
	 					"url" : "codeSNOMED",
	 					"text" : 0
	 					}]} )
	 			existe = ConceptosNoEncontrados.objects.filter(concepto = data).first()
	 			if not existe:
	 				ConceptosNoEncontrados.objects.create(concepto = data)
			print("--- %s seconds Resource Medication ---" % (time.time() - start_time))

			




			return Response(responseMA)
	else:
		return Response(status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def ProcesarMedicationAdministrationView(request):
	responseMA = request.data
	if (responseMA):
		recurso = responseMA['resourceType']
		if (recurso == 'MedicationAdministration'):
			start_time = time.time()
			if 'dosage' in responseMA:
		 		if 'method' in responseMA['dosage']:
			 		metodo = normalize(responseMA['dosage']['method'])
	 				descripciones = DescriptionS.objects.filter(term = metodo) & DescriptionS.objects.filter(category_id = 8)
		 			sinonimos = Synonyms.objects.filter(term = metodo)
		 			if descripciones.count() > 1:
			 			for i in descripciones:
			 				con = ConceptS.objects.get(id = i.conceptid)
			 				if con.active == '0':
			 					descripciones = descripciones.exclude(id=i.id)
		 			if sinonimos.count() > 1:
		 	 			for i in sinonimos:
		 		 			con = ConceptS.objects.get(id = i.conceptid)
		 		 			if con.active == '0':
		 		 				sinonimos = sinonimos.exclude(id=i.id)
		 			if descripciones:
		 				concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
		 				if concepto.active == '1':
		 					responseMA.update( {"extension": [{
		 					"url" : "methodSNOMEDActivo",
		 					"text" : descripciones[0].conceptid
		 					}]} ) 
		 				else:
		 					responseMA.update( {"extension": [{
		 					"url" : "methodSNOMEDInactivo",
		 					"text" : descripciones[0].conceptid
		 					}]} ) 
		 			elif sinonimos:
		 				concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
		 				if concepto.active == '1':
		 					responseMA.update( {"extension": [{
		 					"url" : "methodSNOMEDActivo",
		 					"text" : sinonimos[0].conceptid
		 					}]} ) 
		 				else:
		 					responseMA.update( {"extension": [{
		 					"url" : "methodSNOMEDInactivo",
		 					"text" : sinonimos[0].conceptid
		 					}]} ) 
		 			else:
		 				responseMA.update( {"extension": [{
		 					"url" : "methodSNOMEDInactivo",
		 					"text" : 0
		 					}]} ) 
		 				existe = ConceptosNoEncontrados.objects.filter(concepto = metodo).first()
			 			if not existe:
			 				#print("entre en if not existe de administracion con metodo = "+ metodo)
			 				ConceptosNoEncontrados.objects.create(concepto = metodo)

			if 'dosage' in responseMA:
		 		if 'route' in responseMA['dosage']:
		 			#ruta = normalize(val['resource']['dosage']['route'].encode("latin-1").decode("utf-8"))
		 			ruta = normalize(responseMA['dosage']['route'])
		 			descripciones = DescriptionS.objects.filter(term = ruta) & DescriptionS.objects.filter(category_id = 8)
		 			sinonimos = Synonyms.objects.filter(term = ruta)
		 			if descripciones.count() > 1:
			 			for i in descripciones:
			 				con = ConceptS.objects.get(id = i.conceptid)
			 				if con.active == '0':
			 					descripciones = descripciones.exclude(id=i.id)
		 			if sinonimos.count() > 1:
		 	 			for i in sinonimos:
		 		 			con = ConceptS.objects.get(id = i.conceptid)
		 		 			if con.active == '0':
		 		 				sinonimos = sinonimos.exclude(id=i.id)
		 			if descripciones:
		 				concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
		 				if concepto.active == '1':
		 					responseMA['extension'].append({
		 					"url" : "rutaSNOMEDActivo",
		 					"text" : descripciones[0].conceptid
		 					} ) 
		 					print(responseMA['extension'])
		 				else:
		 					responseMA['extension'].append({
		 					"url" : "rutaSNOMEDInactivo",
		 					"text" : descripciones[0].conceptid
		 					} ) 
	 
	 				elif sinonimos:
	 					concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
	 					if concepto.active == '1':
	 						responseMA['extension'].append({
		 					"url" : "rutaSNOMEDActivo",
		 					"text" : sinonimos[0].conceptid
		 					} ) 
	 					else:
	 						responseMA['extension'].append({
		 					"url" : "rutaSNOMEDActivo",
		 					"text" : sinonimos[0].conceptid
		 					} ) 
	 				else:
	 					responseMA['extension'].append({
		 					"url" : "rutaSNOMED",
		 					"text" : 0
		 					} ) 
	 					existe = ConceptosNoEncontrados.objects.filter(concepto = ruta).first()
			 			if not existe:
			 				ConceptosNoEncontrados.objects.create(concepto = ruta)
			print("--- %s seconds Resource MedicationAdministration ---" % (time.time() - start_time))

			return Response(responseMA)
	else:
		return Response(status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def ProcesarProcedureView(request):
	responseMA = request.data
	if (responseMA):
		recurso = responseMA['resourceType']
		if (recurso == 'Procedure'):
			start_time = time.time()
			if 'code' in responseMA:
	 			procedimiento = normalize(responseMA['code'])
	 			descripciones = DescriptionS.objects.filter(term = procedimiento) & DescriptionS.objects.filter(category_id = 4)
	 			sinonimos = Synonyms.objects.filter(term = procedimiento)
	 			if descripciones.count() > 1:
		 			for i in descripciones:
			 			con = ConceptS.objects.get(id = i.conceptid)
			 			if con.active == '0':
			 				descripciones = descripciones.exclude(id=i.id)
			 			#print(i.term, i.conceptid, con.active)
			 	if sinonimos.count() > 1:
		 			for i in sinonimos:
			 			con = ConceptS.objects.get(id = i.conceptid)
			 			if con.active == '0':
			 				sinonimos = sinonimos.exclude(id=i.id)
			 			#print(i.term, i.conceptid, con.active)
	 			if descripciones:
	 				concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
	 				if concepto.active == '1':
	 					responseMA.update( {"extension": [{
	 					"url" : "codeSNOMEDActivo",
	 					"text" : descripciones[0].conceptid
	 					}]} ) 
	 				else:
	 					responseMA.update( {"extension": [{
	 					"url" : "codeSNOMEDInactivo",
	 					"text" : descripciones[0].conceptid
	 					}]} )
	 			elif sinonimos:
	 				concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
	 				if concepto.active == "1":
	 					responseMA.update( {"extension": [{
	 					"url" : "codeSNOMEDActivo",
	 					"text" : sinonimos[0].conceptid
	 					}]} )
	 				else:
	 					responseMA.update( {"extension": [{
	 					"url" : "codeSNOMEDInactivo",
	 					"text" : sinonimos[0].conceptid
	 					}]} )
	 			else:
	 				responseMA .update( {"extension": [{
	 					"url" : "codeSNOMED",
	 					"text" : 0
	 					}]} )
	 				existe = ConceptosNoEncontrados.objects.filter(concepto = procedimiento).first()
		 			if not existe:
		 				ConceptosNoEncontrados.objects.create(concepto = procedimiento)
			for val1 in responseMA['note']:
	 			procedimiento = normalize(val1['text'])
			print("--- %s seconds Resource Procedure ---" % (time.time() - start_time))
			return Response(responseMA)
	else:
		return Response(status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def ProcesarObservationView(request):
	responseMA = request.data
	if (responseMA):
		recurso = responseMA['resourceType']
		if (recurso == 'Observation'):
			start_time = time.time()
			if 'category' in responseMA:
				for categ in responseMA['category']:
					if 'coding' in categ:
						for cod in categ['coding']:
							if 'display' in cod:
								if 'system' in cod:
									if 'snomed' not in normalize(cod['system']): 
								 		#categoria = normalize(val['resource']['category'].encode("latin-1").decode("utf-8"))
								 		categoria = normalize(cod['display'])
								 		descripciones = DescriptionS.objects.filter(term = categoria)
								 		sinonimos = Synonyms.objects.filter(term = categoria)
								 		if descripciones.count() > 1:
								 			for i in descripciones:
									 			con = ConceptS.objects.get(id = i.conceptid)
									 			if con.active == '0':
									 				descripciones = descripciones.exclude(id=i.id)
									 	if sinonimos.count() > 1:
								 			for i in sinonimos:
									 			con = ConceptS.objects.get(id = i.conceptid)
									 			if con.active == '0':
									 				sinonimos = sinonimos.exclude(id=i.id)
								 		if descripciones:
								 			concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
								 			if concepto.active == '1':
								 				responseMA.update( {"extension": [{
								 					"url" : "categorySNOMEDActivo",
								 					"text" : descripciones[0].conceptid
								 					}]} ) 
								 			else:
								 				responseMA.update( {"extension": [{
								 					"url" : "categorySNOMEDInactivo",
								 					"text" : descripciones[0].conceptid
								 					}]} )
								 		elif sinonimos:
								 			concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
								 			if concepto.active == '1':
								 				responseMA.update( {"extension": [{
								 					"url" : "categorySNOMEDActivo",
								 					"text" : sinonimos[0].conceptid
								 					}]} ) 
								 			else:
								 				responseMA.update( {"extension": [{
								 					"url" : "categorySNOMEDInactivo",
								 					"text" : sinonimos[0].conceptid
								 					}]} ) 

								 		else:
								 			responseMA.update( {"extension": [{
								 					"url" : "categorySNOMED",
								 					"text" : 0
								 					}]} )
								 			existe = ConceptosNoEncontrados.objects.filter(concepto = categoria).first()
								 			if not existe:
								 				ConceptosNoEncontrados.objects.create(concepto = categoria)

			if 'code' in responseMA:
				if 'coding' in responseMA['code']:
					for cod3 in responseMA['code']['coding']:						
						if 'display' in cod3:
							if 'system' in cod3:
								if 'snomed' not in normalize(cod3['system']):
							 		code = normalize(cod3['display'])
							 		descripciones = DescriptionS.objects.filter(term = code)
							 		sinonimos = Synonyms.objects.filter(term = code)
							 		if descripciones.count() > 1:
							 			for i in descripciones:
								 			con = ConceptS.objects.get(id = i.conceptid)
								 			if con.active == '0':
								 				descripciones = descripciones.exclude(id=i.id)
								 			#print(i.term, i.conceptid, con.active)
								 	if sinonimos.count() > 1:
							 			for i in sinonimos:
								 			con = ConceptS.objects.get(id = i.conceptid)
								 			if con.active == '0':
								 				sinonimos = sinonimos.exclude(id=i.id)
								 			#print(i.term, i.conceptid, con.active)
								 	if descripciones:
							 			concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
							 			if concepto.active == '1':
							 				responseMA['extension'].append({
							 					"url" : "codeSNOMEDActivo",
							 					"text" : descripciones[0].conceptid
							 					} ) 
							 			else:
							 				responseMA['extension'].append({
							 					"url" : "codeSNOMEDInactivo",
							 					"text" : descripciones[0].conceptid
							 					} ) 
							 		elif sinonimos:
							 			concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
							 			if concepto.active == '1':
							 				responseMA['extension'].append({
							 					"url" : "codeSNOMEDActivo",
							 					"text" : sinonimos[0].conceptid
							 					} ) 
							 			else:
							 				responseMA['extension'].append({
							 					"url" : "codeSNOMEDInactivo",
							 					"text" : sinonimos[0].conceptid
							 					} ) 
							 		else:
							 			responseMA['extension'].append({
							 					"url" : "codeSNOMED",
							 					"text" : 0
							 					} ) 
							 			existe = ConceptosNoEncontrados.objects.filter(concepto = code).first()
							 			if not existe:
							 				ConceptosNoEncontrados.objects.create(concepto = code)
									 	print("--- %s seconds Resource Observation ---" % (time.time() - start_time))
			return Response(responseMA)
	else:
		return Response(status=status.HTTP_400_BAD_REQUEST)