from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.template.loader import render_to_string 
from django.shortcuts import render
from Aplicacion1.models import ConceptS, DescriptionS, Synonyms, ConceptosNoEncontrados, LoincEspaña
from django.db.models import Q
from Aplicacion1.servicios import generarRequest, normalize, validateJSON
import json
import copy
from api.models import TokensDiagnosticos
from Aplicacion1.servicios import generarRequest, normalize, validateJSON
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
import nltk
import time
import es_core_news_sm

def Sort(sub_li): 
	sub_li.sort(key = lambda x: x[1],reverse=True)
	return sub_li

def Sort_4(sub_li): 
	sub_li.sort(key = lambda x: x[4],reverse=True)
	return sub_li

def ProcesarOracion2(frasePrueba, indexP, val):
	stop_words = set(stopwords.words("spanish"))
	tokens_palabras1 = word_tokenize(frasePrueba)#tokenizo por palabras la frase del texto libre
	tokens_palabras = [t for t in frasePrueba.split()]
	print("tokens_palabras",tokens_palabras)
	print("tokens´_palabras1",tokens_palabras1)
	"""
	for i, s in enumerate(tokens_palabras):
		tokens_palabras[i] = s.lower()#convierto las tokens(palabras) en minusculas
	"""
	#print(tokens_palabras)
	#print(len(tokens_palabras))
	filt_frasePrueba = [w for w in tokens_palabras if not w in stop_words]# se quitan las stopwords de los tokens(palabras)
	#print("filt_frasePrueba", filt_frasePrueba)
	#print(len(filt_frasePrueba))
	id_terminos_de_token=[]
	#bd_tokens = TokensDiagnosticos.objects.all()#jalo de mi bolsa de palabras todo slos tokens existentes
	arreglo = ['enfermedad', 'trastorno']
	bd_tokens = TokensDiagnosticos.objects.raw("SELECT * FROM `api_tokensdiagnosticos` WHERE token IN %s", [tuple(filt_frasePrueba)])
	#print("len(bd_tokens)", len(bd_tokens))
	#print("type(bd_tokens)", type(bd_tokens))
	for indx, i in enumerate(filt_frasePrueba):#por cada token en la frase
		id_terminos_de_token.append([])
		for j in bd_tokens:#por cada token en la bd
			if j.token == i:#si token de frase esta en token de la instancia de la bd
				id_terminos_de_token[indx].append([j.id_descripcion, j.largo_palabras_termino, j.token])#añado id de la descripcion que continee el token de la frase
	#print("len(id_terminos_de_token) antes de quitar los que tienen descripciones ams largas = ", len(id_terminos_de_token))
	#print("id_terminos_de_token antes de acomodo",id_terminos_de_token)
	max=0
	for term in id_terminos_de_token:
		for index, tupla in enumerate(term):
			#print("index, tupla", index, tupla[0])
			if tupla[1]>len(id_terminos_de_token):
				term.remove(term[index])
	for term in id_terminos_de_token:
		Sort(term)
		#print("term",term)
		for desc, lon, token in term:
			if lon>max:
				max=lon
				idMax = desc
		#print(max)
		#print(idMax)
	#print("id_terminos_de_token despues de acomodo",id_terminos_de_token)
	#print("print aqui", id_terminos_de_token)
	#print("len(id_terminos_de_token) despues de quitar los que tienen descripciones ams largas = ", len(id_terminos_de_token))
	termino_correcto=[]
	#print("id_terminos_de_token antes de checar repeticiones", id_terminos_de_token)
	id_terminos_de_token2 = copy.deepcopy(id_terminos_de_token)
	for index_term, term in enumerate(id_terminos_de_token):
		for index, tupla in enumerate(term):
			longitud_termino = tupla[1]
			id_desc=tupla[0]
			cont=0
			for term2 in id_terminos_de_token2:
				
				for index2, tupla2 in enumerate(term2):
					if tupla2[0] == id_desc:
						cont=cont+1
			#print("cont, longitud_termino", cont, longitud_termino)
			if cont == longitud_termino:
				termino_correcto.append(tupla)
	#print("type(termino_correcto)", type(termino_correcto))
	#print("id_terminos_de_token despues de checar repeticiones", termino_correcto)
	termino_correcto2 = copy.deepcopy(termino_correcto)
	#for termino in termino_correcto:
	#	for index, tripleta in enumerate(termino):
	#		print("tripleta", tripleta)
	#print("termino_correcto despues de quitar menos longitud",termino_correcto)
	termino_correct_sin_repetido=[]
	for term in termino_correcto:
		if term[0] not in termino_correct_sin_repetido:
			termino_correct_sin_repetido.append(term[0])
	#print("termino_correct_sin_repetido", termino_correct_sin_repetido)
	conceptos = []
	for term in termino_correct_sin_repetido:
		desc = DescriptionS.objects.filter(id =int(term))
		conceptos.append([desc[0].conceptid, ])
	#print("conceptos", conceptos)
	data=""
	#-----checar si descripcion de concepto esta tal cual en la frase original(toekns_palabras) y generacion de lista de descripciones con id e indice en frase original
	BooleanTalCual =[]
	descSeguncon =[]
	for indxconc, conc in enumerate(conceptos):
		esta=0
		#print("conc", conc[0])
		#print("type(conc)", type(conc[0]))
		descripciones = DescriptionS.objects.filter(conceptid = str(conc[0]))
		#print("descripciones", descripciones)
		for descripcion in descripciones:
			#print("descripcion", descripcion.term)
			#print("frasePrueba", frasePrueba)
			if str(descripcion.term).lower() in str(frasePrueba).lower():
				#print("entre en si esta")
				esta=1
				indice_inicial = str(frasePrueba).lower().find(str(descripcion.term).lower())
				indice_final = indice_inicial + len(descripcion.term)
				descSeguncon.append([descripcion.term, conc[0], indice_inicial, indice_final, len(descripcion.term)])
				"""
				print ("indxconc", indxconc)
				if indxconc == 0:
					frasePrueba2 = copy.deepcopy(frasePrueba)
				indice_inicial = str(frasePrueba).lower().find(str(descripcion.term).lower())
				print("indice_inicial", indice_inicial)
				indice_final = indice_inicial + len(descripcion.term)
				FSN = DescriptionS.objects.get(conceptid = str(conc[0]), typeid = "900000000000003001", active = "1")
				frasePrueba2 = frasePrueba2[:indice_final] + ' ('+FSN.term+') ' + frasePrueba2[indice_final:]
				print("frasePrueba2", frasePrueba2)
				print("indice_final", indice_final)
				"""
		BooleanTalCual.append(esta)
	#print("len(conceptos)", len(conceptos))
	#print("conceptos", conceptos)
	#print("BooleanTalCual", BooleanTalCual)
	
	#print("len(descSeguncon)", len(descSeguncon))
	#print("len(BooleanTalCual)", len(BooleanTalCual))
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
	conceptos3=[]
	Sort_4(descSeguncon)

	for elitem1 in descSeguncon[::-1]:
		for elitem2 in descSeguncon[::-1]:
			if elitem1 != elitem2:
				if elitem2[2] >=  elitem1[2] and elitem2[2] <= elitem1[3] and elitem2[3] > elitem1[2] and elitem2[3] <= elitem1[3]:
					#print("elitem2 = "+elitem2[0]+" esta en elitem1 = "+elitem1[0])
					if elitem2 in descSeguncon:
						descSeguncon.remove(elitem2)
	#print("descSeguncon", descSeguncon)

	"""
	for ic2, c2 in enumerate(conceptos2):
		for indexItem, ItemDesc in enumerate(descSeguncon):
			print("c2", c2[0])
			print("ItemDesc[1]", ItemDesc[1])
			if c2[0] == ItemDesc[1]:
				for indexItem2, ItemDesc2 in enumerate(descSeguncon):
					if ItemDesc != ItemDesc2:
						if ItemDesc2[2] >=  ItemDesc[2] and ItemDesc2[2] <= ItemDesc[3] and ItemDesc2[3] > ItemDesc[2] and ItemDesc2[3] <= ItemDesc[3]:
							print("agregue = "+c2[0])
							if c2 not in conceptos3:
								conceptos3.append(c2)
								"""
	for itemotro in descSeguncon:
		conceptos3.append([itemotro[1]] )
	frasePrueba2=""

	#print("conceptos2 ya quiando los substrings", conceptos3)
	aumento=0
	for indxconc3, conc3 in enumerate(conceptos3):
		descripciones = DescriptionS.objects.filter(conceptid = str(conc3[0]))
		for descripcion in descripciones:
			if str(descripcion.term).lower() in str(frasePrueba).lower():
				cont=cont+1
				#print ("indxconc", indxconc3)
				if indxconc3 == 0:
					frasePrueba2 = copy.deepcopy(frasePrueba)
				indice_inicial = str(frasePrueba2).lower().find(str(descripcion.term).lower())
				#print("indice_inicial", indice_inicial)
				indice_final = indice_inicial + len(descripcion.term)
				FSN = DescriptionS.objects.get(conceptid = str(conc3[0]), typeid = "900000000000003001", active = "1")
				frasePrueba2 = frasePrueba2[:(indice_final)] + ' ('+FSN.term+')' + frasePrueba2[(indice_final):]
				#if cont == 1:
				#	aumento = aumento + len(FSN.term)+4
				#else:
				#	aumento=aumento + len(FSN.term)
				#print("frasePrueba2", frasePrueba2)
				#print("indice_final", indice_final)
	#print("conceptos3",conceptos3)


	if len(conceptos3) >= 1:
		for indexItem, item in enumerate(conceptos3):
			print(indexItem)
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
	if frasePrueba2 == "":
		return frasePrueba
	else:
		return frasePrueba2
	
	#val['resource'].update( {"conclusion": frasePrueba2} )
	#print("--- %s seconds ---" % (time.time() - start_time))
# Create your views here.

@api_view(['GET'])
def apiOverview(request):
	api_urls = {
		'ProcesarSNOMED': '/procesarSNOMED/'
	}
	return Response(api_urls)

@api_view(['POST'])
def ProcesarView(request):
	recurso = 'bundle'
	if (recurso == 'bundle'):
		 start_time = time.time()
		 responseMA = request.data
		 responseMA1 = copy.deepcopy(responseMA)
		 for val in responseMA['entry']:
		 	#print("val")
		 	#print(val)

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
			 				#val['resource'].update({"codeSNOMED": descripciones[0].conceptid})
			 				#val['resource'].update({"status_codeSNOMED": "activo"})
			 			else:
			 				val['resource'].update( {"extension": [{
			 					"url" : "codeSNOMEDInactivo",
			 					"text" : descripciones[0].conceptid
			 					}]} ) 
			 				#val['resource'].update({"codeSNOMED": descripciones[0].conceptid})
			 				#val['resource'].update({"status_codeSNOMED": "inactivo"})
			 		elif sinonimos:
			 			concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
			 			if concepto.active == '1':
			 				val['resource'].update( {"extension": [{
			 					"url" : "codeSNOMEDActivo",
			 					"text" : sinonimos[0].conceptid
			 					}]} ) 
			 				#val['resource'].update({"codeSNOMED": sinonimos[0].conceptid})
			 				#val['resource'].update({"status_codeSNOMED": "activo"})
			 			else:
			 				val['resource'].update( {"extension": [{
			 					"url" : "codeSNOMEDInactivo",
			 					"text" : sinonimos[0].conceptid
			 					}]} ) 
			 				#val['resource'].update({"codeSNOMED": sinonimos[0].conceptid})
			 				#val['resource'].update({"status_codeSNOMED": "inactivo"})
			 		else:
			 			val['resource'].update( {"extension": [{
			 					"url" : "codeSNOMED",
			 					"text" : 0
			 					}]} )
			 			#val['resource'].update({"codeSNOMED": 0})
			 			existe = ConceptosNoEncontrados.objects.get(concepto = data)
			 			if not existe:
			 				ConceptosNoEncontrados.objects.create(concepto = data)
			 	print("--- %s seconds Resource Medication ---" % (time.time() - start_time))

		 	if "MedicationAdministration" == val['resource']['resourceType']:
		 		if 'dosage' in val['resource']:
			 		if 'method' in val['resource']['dosage']:
			 			#metodo = normalize(val['resource']['dosage']['method'].encode("latin-1").decode("utf-8"))
				 		metodo = normalize(val['resource']['dosage']['method'])
		 				descripciones = DescriptionS.objects.filter(term = metodo) & DescriptionS.objects.filter(category_id = 8)
			 			sinonimos = Synonyms.objects.filter(term = metodo)
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
			 					"url" : "methodSNOMEDActivo",
			 					"text" : descripciones[0].conceptid
			 					}]} ) 
			 					#val['resource']['dosage'].update({"methodSNOMED": descripciones[0].conceptid})
			 					#val['resource']['dosage'].update({"status_methodSNOMED": "activo"})
			 				else:
			 					val['resource'].update( {"extension": [{
			 					"url" : "methodSNOMEDInactivo",
			 					"text" : descripciones[0].conceptid
			 					}]} ) 
			 					#val['resource']['dosage'].update({"methodSNOMED": descripciones[0].conceptid})
			 					#val['resource']['dosage'].update({"status_methodSNOMED": "inactivo"})
			 			elif sinonimos:
			 				concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
			 				if concepto.active == '1':
			 					val['resource'].update( {"extension": [{
			 					"url" : "methodSNOMEDActivo",
			 					"text" : sinonimos[0].conceptid
			 					}]} ) 
			 					#val['resource']['dosage'].update({"methodSNOMED": sinonimos[0].conceptid})
			 					#val['resource']['dosage'].update({"status_methodSNOMED": "activo"})
			 				else:
			 					val['resource'].update( {"extension": [{
			 					"url" : "methodSNOMEDInactivo",
			 					"text" : sinonimos[0].conceptid
			 					}]} ) 
			 					#val['resource']['dosage'].update({"methodSNOMED": sinonimos[0].conceptid})
			 					#val['resource']['dosage'].update({"status_methodSNOMED": "inactivo"})
			 			else:
			 				val['resource'].update( {"extension": [{
			 					"url" : "methodSNOMEDInactivo",
			 					"text" : 0
			 					}]} ) 
			 				#val['resource']['dosage'].update({"metodoSNOMED": 0})
			 				existe = ConceptosNoEncontrados.objects.get(concepto = metodo)
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
			 					"url" : "rutaSNOMEDActivo",
			 					"text" : descripciones[0].conceptid
			 					} ) 
			 					print(val['resource']['extension'])
			 					#val['resource']['dosage'].update({"rutaSNOMED": descripciones[0].conceptid})
			 					#val['resource']['dosage'].update({"status_rutaSNOMED": "activo"})
			 				else:
			 					val['resource']['extension'].append({
			 					"url" : "rutaSNOMEDInactivo",
			 					"text" : descripciones[0].conceptid
			 					} ) 
			 					#val['resource']['dosage'].update({"rutaSNOMED": descripciones[0].conceptid})
			 					#val['resource']['dosage'].update({"status_rutaSNOMED": "inactivo"})
		 
		 				elif sinonimos:
		 					concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
		 					if concepto.active == '1':
		 						val['resource']['extension'].append({
			 					"url" : "rutaSNOMEDActivo",
			 					"text" : sinonimos[0].conceptid
			 					} ) 
		 						#val['resource']['dosage'].update({"rutaSNOMED": sinonimos[0].conceptid})
		 						#val['resource']['dosage'].update({"status_rutaSNOMED": "activo"})
		 					else:
		 						val['resource']['extension'].append({
			 					"url" : "rutaSNOMEDActivo",
			 					"text" : sinonimos[0].conceptid
			 					} ) 
		 						#val['resource']['dosage'].update({"rutaSNOMED": sinonimos[0].conceptid})
		 						#val['resource']['dosage'].update({"status_rutaSNOMED": "inactivo"})
		 				else:
		 					val['resource']['extension'].append({
			 					"url" : "rutaSNOMED",
			 					"text" : 0
			 					} ) 
		 					#val['resource']['dosage'].update({"rutaSNOMED": 0})
		 					existe = ConceptosNoEncontrados.objects.get(concepto = ruta)
				 			if not existe:
				 				print("entre en if not existe de administracion con ruta = "+ ruta)
				 				ConceptosNoEncontrados.objects.create(concepto = ruta)
			 	print("--- %s seconds Resource MedicationAdministration ---" % (time.time() - start_time))
		 	if "DiagnosticReport" == val['resource']['resourceType']:
		 		if 'conclusionCode' in val['resource']:
			 		#conclusion = normalize(val['resource']['conclusion'].encode("latin-1").decode("utf-8"))
			 		conclusionCode = normalize(val['resource']['conclusionCode'])
			 		descripciones = DescriptionS.objects.filter(term = conclusionCode) & DescriptionS.objects.filter(category_id = 6)
			 		sinonimos = Synonyms.objects.filter(term = conclusionCode)
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
			 					"url" : "conclusionCodeSNOMEDActivo",
			 					"text" : descripciones[0].conceptid
			 					}]} ) 
			 				#val['resource'].update({"conclusionSNOMED": descripciones[0].conceptid})
			 				#val['resource'].update({"status_conclusionSNOMED": "activo"})
			 			else:
			 				val['resource'].update( {"extension": [{
			 					"url" : "conclusionCodeSNOMEDInactivo",
			 					"text" : descripciones[0].conceptid
			 					}]} ) 
			 				#val['resource'].update({"conclusionSNOMED": descripciones[0].conceptid})
			 				#val['resource'].update({"status_conclusionSNOMED": "inactivo"})
			 		elif sinonimos:
			 			concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
			 			if concepto.active == '1':
			 				val['resource'].update( {"extension": [{
			 					"url" : "conclusionCodeSNOMEDActivo",
			 					"text" : sinonimos[0].conceptid
			 					}]} ) 
			 				#val['resource'].update({"conclusionSNOMED": sinonimos[0].conceptid})
			 				#val['resource'].update({"status_conclusionSNOMED": "activo"})
			 			else:
			 				val['resource'].update( {"extension": [{
			 					"url" : "conclusionCodeSNOMEDInactivo",
			 					"text" : sinonimos[0].conceptid
			 					}]} ) 
			 				#val['resource'].update({"conclusionSNOMED": sinonimos[0].conceptid})
			 				#val['resource'].update({"status_conclusionSNOMED": "inactivo"})
			 		else:
			 			val['resource'].update( {"extension": [{
			 					"url" : "conclusionCodeSNOMED",
			 					"text" : 0
			 					}]} ) 
			 			#val['resource'].update({"conclusionSNOMED": 0})
			 			existe = ConceptosNoEncontrados.objects.get(concepto = conclusion)
			 			if not existe:
			 				ConceptosNoEncontrados.objects.create(concepto = conclusion)
			 	if 'conclusion' in val['resource']:
			 		frasePrueba = normalize(val['resource']['conclusion']).lower()
			 		stop_words = set(stopwords.words("spanish"))
			 		frasePrueba = frasePrueba.replace(',', '.')
			 		tokens_frases = sent_tokenize(frasePrueba)
			 		#print("token_frases antes de funcion", tokens_frases)
			 		fraseFinal = ""
			 		if tokens_frases:
			 			for indx, frases in enumerate(tokens_frases):
			 				if indx == 0:
			 					fraseFinal = fraseFinal + ProcesarOracion2(frases, indx, val).capitalize()
			 				else:
			 					fraseFinal = fraseFinal + " "+ ProcesarOracion2(frases, indx, val).capitalize()
			 				#ProcesarOracion2(frases, indx, val)
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
		 					#val1.update({"textSNOMED": descripciones[0].conceptid})
		 					#val1.update({"status_textSNOMED": "activo"})
		 				else:
		 					val['resource'].update( {"extension": [{
		 					"url" : "codeSNOMEDInactivo",
		 					"text" : descripciones[0].conceptid
		 					}]} )
		 					#val1.update({"textSNOMED": descripciones[0].conceptid})
		 					#val1.update({"status_textSNOMED": "inactivo"})
		 			elif sinonimos:
		 				concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
		 				if concepto.active == "1":
		 					val['resource'].update( {"extension": [{
		 					"url" : "codeSNOMEDActivo",
		 					"text" : sinonimos[0].conceptid
		 					}]} )
		 					#val1.update({"textSNOMED": sinonimos[0].conceptid})
		 					#val1.update({"status_textSNOMED": "activo"})
 						else:
 							val['resource'].update( {"extension": [{
		 					"url" : "codeSNOMEDInactivo",
		 					"text" : sinonimos[0].conceptid
		 					}]} )
 							#val1.update({"textSNOMED": sinonimos[0].conceptid})
 							#val1.update({"status_textSNOMED": "inactivo"})
 					else:
 						#print("entre en else de procedure con procedimeinto = "+ procedimiento)
 						val['resource'] .update( {"extension": [{
		 					"url" : "codeSNOMED",
		 					"text" : 0
		 					}]} )
 						#val1.update({"textSNOMED": 0})
 						existe = ConceptosNoEncontrados.objects.filter(concepto = procedimiento).first()
			 			if not existe:
			 				#print("entre en if not existe de procedure con procedimeinto = "+ procedimiento)
			 				ConceptosNoEncontrados.objects.create(concepto = procedimiento)
		 		for val1 in val['resource']['note']:
		 			#procedimiento = normalize(val1['text'].encode("latin-1").decode("utf-8"))
		 			procedimiento = normalize(val1['text'])
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
			 					"url" : "categorySNOMEDActivo",
			 					"text" : descripciones[0].conceptid
			 					}]} ) 
			 				#val['resource'].update({"categorySNOMED": descripciones[0].conceptid})
			 				#val['resource'].update({"status_categorySNOMED": "activo"})
			 			else:
			 				val['resource'].update( {"extension": [{
			 					"url" : "categorySNOMEDInactivo",
			 					"text" : descripciones[0].conceptid
			 					}]} )
			 				#val['resource'].update({"categorySNOMED": descripciones[0].conceptid})
			 				#val['resource'].update({"status_categorySNOMED": "inactivo"})
			 		elif sinonimos:
			 			concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
			 			if concepto.active == '1':
			 				val['resource'].update( {"extension": [{
			 					"url" : "categorySNOMEDActivo",
			 					"text" : sinonimos[0].conceptid
			 					}]} ) 
			 				#val['resource'].update({"categorySNOMED": sinonimos[0].conceptid})
			 				#val['resource'].update({"status_categorySNOMED": "activo"})
			 			else:
			 				val['resource'].update( {"extension": [{
			 					"url" : "categorySNOMEDInactivo",
			 					"text" : sinonimos[0].conceptid
			 					}]} ) 
			 				#val['resource'].update({"categorySNOMED": sinonimos[0].conceptid})
			 				#val['resource'].update({"status_categorySNOMED": "inactivo"})

			 		else:
			 			val['resource'].update( {"extension": [{
			 					"url" : "categorySNOMED",
			 					"text" : 0
			 					}]} )
			 			#val['resource'].update({"categorySNOMED": 0})
			 			existe = ConceptosNoEncontrados.objects.filter(concepto = categoria).first()
			 			if not existe:
			 				ConceptosNoEncontrados.objects.create(concepto = categoria)

		 		if 'code' in val['resource']:
			 		#code = normalize(val['resource']['code'].encode("latin-1").decode("utf-8"))
			 		code = normalize(val['resource']['code'])
			 		descripciones = DescriptionS.objects.filter(term = code)
			 		#print("descripciones: termino--esta activo?" + code)
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
			 				#val['resource'].update({"codeSNOMED": descripciones[0].conceptid})
			 				#val['resource'].update({"status_codeSNOMED": "activo"})
			 			else:
			 				val['resource']['extension'].append({
			 					"url" : "codeSNOMEDInactivo",
			 					"text" : descripciones[0].conceptid
			 					} ) 
			 				#val['resource'].update({"codeSNOMED": descripciones[0].conceptid})
			 				#val['resource'].update({"status_codeSNOMED": "inactivo"})
			 		elif sinonimos:
			 			concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
			 			if concepto.active == '1':
			 				val['resource']['extension'].append({
			 					"url" : "codeSNOMEDActivo",
			 					"text" : sinonimos[0].conceptid
			 					} ) 
			 				#val['resource'].update({"codeSNOMED": sinonimos[0].conceptid})
			 				#val['resource'].update({"codeSNOMED": "activo"})
			 			else:
			 				val['resource']['extension'].append({
			 					"url" : "codeSNOMEDInactivo",
			 					"text" : sinonimos[0].conceptid
			 					} ) 
			 				#val['resource'].update({"codeSNOMED": sinonimos[0].conceptid})
			 				#val['resource'].update({"codeSNOMED": "inactivo"})
	 				else:
	 					val['resource']['extension'].append({
			 					"url" : "codeSNOMED",
			 					"text" : 0
			 					} ) 
	 					#val['resource'].update({"codeSNOMED": 0})
	 					existe = ConceptosNoEncontrados.objects.get(concepto = code)
			 			if not existe:
			 				ConceptosNoEncontrados.objects.create(concepto = code)
			 	print("--- %s seconds Resource Observation ---" % (time.time() - start_time))

		 data=""
		 print("--- %s seconds ---" % (time.time() - start_time))

	return Response(responseMA)
