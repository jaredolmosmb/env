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


#------Funcion para procesar el motor de búsqueda en una oración
def ProcesarOracion(frasePrueba, indx, responseMA, responseMA1, start_time):
	stop_words = set(stopwords.words("spanish"))
	#tokens_palabras = word_tokenize(frasePrueba)#tokenizo por palabras la frase del texto libre
	tokens_palabras = [t for t in frasePrueba.split()]
	#print(tokens_palabras)
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
	print("len(bd_tokens)", len(bd_tokens))
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
	#-----checar si descripcion de concepto esta tal cual en la frase original(toekns_palabras)
	BooleanTalCual =[]
	for conc in conceptos:
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
		BooleanTalCual.append(esta)
	#print("conceptos", conceptos)
	#print("BooleanTalCual", BooleanTalCual)
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
	#print("conceptos ya rmeoviendo los no talcual", conceptos2)
	if len(conceptos2) >= 1:
		for indexItem, item in enumerate(conceptos2):
			if "extension" not in responseMA:
				responseMA.update( {"extension": [{
				"url" : "codeSNOMEDActivo1 ",
				"text" : item[0]
				}]} )
			else:
				responseMA["extension"].append( {
				"url" : "codeSNOMEDActivo1 ",
				"text" : item[0]
				} )
		#print("responseMA", responseMA)
	if termino_correcto:
		for index, tupla in enumerate(termino_correcto):
			data=data + " "+ tupla[0]
	else:
		data=""
	print("--- %s seconds ---" % (time.time() - start_time))

#funicon para probar el procesamiento de distintos recursos de FHIR sin modificar la api
def InicioView(request):
	#pacientes = Paciente.objects.all()
	recurso = 'cie10'

	if (recurso == 'cie10'):
		mapeo = ExtendedmaprefsetS.objects.all()
		cont6 = 0
		cont13 = 0
		cont15 = 0
		cont1 = 0
		cont16 = 0
		cont5 = 0
		lista_categorias = []
		for elemento in mapeo:
			concepto = ConceptS.objects.get(id = elemento.referencedcomponentid)
			print(concepto)
			if concepto.active == "1":	
				print("entre en if de concept active")			
				FSN = DescriptionS.objects.filter(conceptid = elemento.referencedcomponentid, typeid = "900000000000003001", active = "1")
				print("len(FSN)",len(FSN))

				if FSN[0].category_id == 6:
					cont6 = cont6+1
				if FSN[0].category_id == 13:
					cont13 = cont13+1
				if FSN[0].category_id == 15:
					cont15 = cont15+1
				if FSN[0].category_id == 1:
					cont1 = cont1+1
				if FSN[0].category_id == 16:
					cont16 = cont16+1
				if FSN[0].category_id == 5:
					cont5 = cont5+1
				if FSN[0].category_id not in lista_categorias:
					lista_categorias.append(FSN[0].category_id)

			#print(FSN.term)

		print(lista_categorias)
		print("cont6, cont13, cont15, cont1, cont16, cont5", cont6, cont13, cont15, cont1, cont16, cont5)
	if (recurso == 'analisisDiagnosticoF'):
		start_time = time.time()
		with open("TextoLibreDiagnostico.json", "r") as read_file:
			try:
				responseMA = json.load(read_file)
				responseMA1 = copy.deepcopy(responseMA)
				#print("valido")
				isValid = True
			except ValueError as err:
				#print("invalido")
				isValid = False
		if isValid:
			if 'conclusion' in responseMA:
				#print("entre en conclusion")
				frasePrueba = normalize(responseMA['conclusion']).encode("latin-1").decode("utf-8").lower()
				#frasePrueba1 = "El sistema financiero, hemorragia coroidea (transtorno), para los efectos de esta Ley, se compone por el Banco de México, las instituciones de crédito, de seguros y de fianzas, sociedades controladoras de grupos financieros, almacenes generales de depósito, administradoras de fondos para el retiro, arrendadoras financieras, uniones de crédito, sociedades financieras populares, fondos de inversión de renta variable, fondos de inversión en instrumentos de deuda, empresas de factoraje financiero, casas de bolsa, y casas de cambio, que sean residentes en México o en el extranjero. Se considerarán integrantes del sistema financiero a las sociedades financieras de objeto múltiple a las que se refiere la Ley General de Organizaciones y Actividades Auxiliares del Crédito que tengan cuentas y documentos por cobrar derivados de las actividades que deben constituir su objeto social principal, conforme a lo dispuesto en dicha Ley, que representen al menos el 70% de sus activos totales, o bien, que tengan ingresos derivados de dichas actividades y de la enajenación o administración de los créditos otorgados por ellas, que representen al menos el 70% de sus ingresos totales. Para los efectos de la determinación del porcentaje del 70%, no se considerarán los activos o ingresos que deriven de la enajenación a crédito de bienes o servicios de las propias sociedades, de las enajenaciones que se efectúen con cargo a tarjetas de crédito o financiamientos otorgados por terceros. Trastorno de ansiedad de la niñez O la adolescencia"
				#frasePrueba = "Trastorno de ansiedad de la niñez O la adolescencia ley de cosas"
				#print("frasePrueba", frasePrueba)
				#print("frasePrueba1", frasePrueba1)
				stop_words = set(stopwords.words("spanish"))
				#print ("stop_words", stop_words)
				tokens_frases = sent_tokenize(frasePrueba)
				#print("tokens_frases", tokens_frases)
				#print("len(token_frases)", len(tokens_frases))
				if tokens_frases:
					print("entre a procesamiento de mas de una frase")
					for indx, frases in enumerate(tokens_frases):
						ProcesarOracion(frases, indx, responseMA, responseMA1, start_time)
				"""else:#procesamiento de una sola frase
					#tokens_palabras = word_tokenize(frasePrueba)#tokenizo por palabras la frase del texto libre
					tokens_palabras = [t for t in frasePrueba.split()]
					#print(tokens_palabras)
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
					#-----checar si descripcion de concepto esta tal cual en la frase original(toekns_palabras)
					BooleanTalCual =[]
					for conc in conceptos:
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
						BooleanTalCual.append(esta)
					#print("conceptos", conceptos)
					#print("BooleanTalCual", BooleanTalCual)
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
					#print("conceptos ya rmeoviendo los no talcual", conceptos2)
					if len(conceptos2) >= 1:
						for indexItem, item in enumerate(conceptos2):
							if "extension" not in responseMA:
								responseMA.update( {"extension": [{
								"url" : "codeSNOMEDActivo1 ",
								"text" : item[0]
								}]} )
							else:
								responseMA["extension"].append( {
								"url" : "codeSNOMEDActivo1 ",
								"text" : item[0]
								} )
						#print("responseMA", responseMA)
					if termino_correcto:
						for index, tupla in enumerate(termino_correcto):
							data=data + " "+ tupla[0]
					else:
						data=""
					print("--- %s seconds ---" % (time.time() - start_time))
		else:
			responseMA ={"status": "json invalido"}
			responseMA1 = copy.deepcopy(responseMA)
			data=""
			"""
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

			for i in concepto1[0:115484]:
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
	if (recurso == 'analisisProcedure'):
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
			#frasePrueba = "El sistema financiero, para los efectos de esta Ley, se compone por el Banco de México, las instituciones de crédito, de seguros y de fianzas, sociedades controladoras de grupos financieros, almacenes generales de depósito, administradoras de fondos para el retiro, arrendadoras financieras, uniones de crédito, sociedades financieras populares, fondos de inversión de renta variable, fondos de inversión en instrumentos de deuda, empresas de factoraje financiero, casas de bolsa, y casas de cambio, que sean residentes en México o en el extranjero. Se considerarán integrantes del sistema financiero a las sociedades financieras de objeto múltiple a las que se refiere la Ley General de Organizaciones y Actividades Auxiliares del Crédito que tengan cuentas y documentos por cobrar derivados de las actividades que deben constituir su objeto social principal, conforme a lo dispuesto en dicha Ley, que representen al menos el 70% de sus activos totales, o bien, que tengan ingresos derivados de dichas actividades y de la enajenación o administración de los créditos otorgados por ellas, que representen al menos el 70% de sus ingresos totales. Para los efectos de la determinación del porcentaje del 70%, no se considerarán los activos o ingresos que deriven de la enajenación a crédito de bienes o servicios de las propias sociedades, de las enajenaciones que se efectúen con cargo a tarjetas de crédito o financiamientos otorgados por terceros.trastorno de ansiedad de la niñez O la adolescencia"
			stop_words = set(stopwords.words("spanish"))
			#print("stopwords", stop_words)
			descripciones = DescriptionS.objects.filter(category_id = 4)
			#print(type(descripciones))
			#print (descripciones.count())
			descAceptadas =[]

			start_time = time.time()
			concepto1 = ConceptS.objects.filter(active ="1") and ConceptS.objects.filter(category_id ="4")
			print("concepto1.coun", concepto1.count())

			for i in concepto1[30001:50000]:
				desc = DescriptionS.objects.filter(conceptid = i.id)
				for j in desc:
					#print(j.term)
					tokens = [t for t in j.term.split()]
					#tokens = word_tokenize(j.term)
					filt_tokens = [w.lower() for w in tokens if not w.lower() in stop_words]
					for k in filt_tokens:
						TokensProcedures.objects.create(token=k.lower(), id_descripcion=j.id, largo_palabras_termino=len(filt_tokens))
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
	if (recurso == 'analisisAdministracion'):
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
			textoLibre = responseMA['dosage']['text']
			#print("textolibre", textoLibre)
			method=""
			doseValue=""
			doseUnit=""
			data=""
			tokens = word_tokenize(textoLibre)
			#tokens = [t for t in textoLibre.split()]
			print (tokens)
			nlp = es_core_news_sm.load()
			doc = nlp(textoLibre)
			#print("tipo doc", type(doc))
			#print([(w.text, w.pos_, w.dep_) for w in doc])
			for w in doc:
				#print(w.i)
				if w.pos_ == 'VERB':
					method = normalize((w.text).encode("latin-1").decode("utf-8")).lower()
				if w.pos_ == 'NUM':
					for uni in unidades:
						if str(uni) == normalize(str(doc[w.i+1]).encode("latin-1").decode("utf-8")).lower():
							doseValue = w.text
							doseUnit = uni
				if normalize((w.text).encode("latin-1").decode("utf-8")).lower() == 'via':
					#print(normalize((str(doc[w.i+1]) +" "+ str(doc[w.i+2])).encode("latin-1").decode("utf-8")).lower())
					if normalize((str(doc[w.i+1]) +" "+ str(doc[w.i+2])).encode("latin-1").decode("utf-8")).lower() == "de administracion":
						route = normalize((str(doc[w.i])+" "+str(doc[w.i+1]) +" "+ str(doc[w.i+2])+" "+str(doc[w.i+3])).encode("latin-1").decode("utf-8")).lower()
					else:
						route = normalize((str(doc[w.i])+" "+str(doc[w.i+1])).encode("latin-1").decode("utf-8")).lower()
						


			print("method", method)
			print("doseValue", doseValue)
			print("doseUnit", doseUnit)
			print("route", route)

			responseMA["dosage"].update({"method": method})
			responseMA["dosage"].update({"route": route})
			responseMA["dosage"]["dose"].update({"value": doseValue})
			responseMA["dosage"]["dose"].update({"unit": doseUnit})



			data = doc

		else:
			responseMA ={"status": "json invalido"}
			responseMA1 = copy.deepcopy(responseMA)
			data=""
	if (recurso == 'medicamento'):
		"""
		# recibir json de servidor
		params=""
		responseMA = generarRequest('https://stu3.test.pyrohealth.net/fhir/Medication/38b07e0f-1012-4c68-b9b8-c912dee57414')
		responseMA1 = generarRequest('https://stu3.test.pyrohealth.net/fhir/Medication/38b07e0f-1012-4c68-b9b8-c912dee57414')
		data = responseMA1['code']['text']
		#-----
		"""
		with open("medicamento.json", "r") as read_file:
			try:
				responseMA = json.load(read_file)
				responseMA1 = copy.deepcopy(responseMA)
				print("valido")
				isValid = True
			except ValueError as err:
				print("invalido")
				isValid = False
		if isValid:
			data = normalize(responseMA['code'].encode("latin-1").decode("utf-8"))

			descripciones = DescriptionS.objects.filter(term = data) & DescriptionS.objects.filter(category_id = 10)

			sinonimos = Synonyms.objects.filter(term = data)
			if descripciones:
				concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
				if concepto.active == '1':
					responseMA.update({"codeSNOMED": descripciones[0].conceptid})
					responseMA.update({"status_codeSNOMED": "activo"})
				else:
					responseMA.update({"codeSNOMED": descripciones[0].conceptid})
					responseMA.update({"status_codeSNOMED": "inactivo"})
			elif sinonimos:
				concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
				if concepto.active == '1':
					responseMA.update({"codeSNOMED": sinonimos[0].conceptid})
					responseMA.update({"status_codeSNOMED": "activo"})
				else:
					responseMA.update({"codeSNOMED": sinonimos[0].conceptid})
					responseMA.update({"status_codeSNOMED": "inactivo"})
			else:
				responseMA.update({"codeSNOMED": 0})

			print('json inicial')
			print(responseMA1)
			print('json resultado')
			print(responseMA)

		else:
			responseMA ={"status": "json invalido"}
			responseMA1 = copy.deepcopy(responseMA)
			data=""
	if (recurso == 'administracion'):
		"""
		# recibir json de servidor
		params=""
		responseMA = generarRequest('https://stu3.test.pyrohealth.net/fhir/MedicationAdministration/eaa49779-81a5-47d6-9b2e-52e8d6786059')
		responseMA1 = generarRequest('https://stu3.test.pyrohealth.net/fhir/MedicationAdministration/eaa49779-81a5-47d6-9b2e-52e8d6786059')
		data = responseMA1['medicationCodeableConcept']['text']
		#-----
		"""
		with open("administracion.json", "r") as read_file:
			try:
				responseMA = json.load(read_file)
				responseMA1 = copy.deepcopy(responseMA)
				print("valido")
				isValid = True
			except ValueError as err:
				print("invalido")
				isValid = False
		if isValid:
			metodo = responseMA['dosage']['method']
			descripciones = DescriptionS.objects.filter(term = metodo) & DescriptionS.objects.filter(category_id = 8)
			sinonimos = Synonyms.objects.filter(term = metodo)
			if descripciones:
				concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
				if concepto.active == '1':
					responseMA['dosage'].update({"metodoSNOMED": descripciones[0].conceptid})
					responseMA['dosage'].update({"status_metodoSNOMED": "activo"})
				else:
					responseMA['dosage'].update({"metodoSNOMED": descripciones[0].conceptid})
					responseMA['dosage'].update({"status_metodoSNOMED": "inactivo"})
			elif sinonimos:
				concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
				if concepto.active == '1':
					responseMA['dosage'].update({"metodoSNOMED": sinonimos[0].conceptid})
					responseMA['dosage'].update({"status_metodoSNOMED": "activo"})
				else:
					responseMA['dosage'].update({"metodoSNOMED": sinonimos[0].conceptid})
					responseMA['dosage'].update({"status_metodoSNOMED": "inactivo"})
			else:
				responseMA['dosage'].update({"metodoSNOMED": 0})
			print('json inicial')
			print(responseMA1)


			ruta = responseMA['dosage']['route']
			descripciones = DescriptionS.objects.filter(term = ruta) & DescriptionS.objects.filter(category_id = 8)
			sinonimos = Synonyms.objects.filter(term = ruta)
			if descripciones:
				concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
				if concepto.active == '1':
					responseMA['dosage'].update({"rutaSNOMED": descripciones[0].conceptid})
					responseMA['dosage'].update({"status_rutaSNOMED": "activo"})
				else:
					responseMA['dosage'].update({"rutaSNOMED": descripciones[0].conceptid})
					responseMA['dosage'].update({"status_rutaSNOMED": "inactivo"})

			elif sinonimos:
				concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
				if concepto.active == '1':
					responseMA['dosage'].update({"rutaSNOMED": sinonimos[0].conceptid})
					responseMA['dosage'].update({"status_rutaSNOMED": "activo"})
				else:
					responseMA['dosage'].update({"rutaSNOMED": sinonimos[0].conceptid})
					responseMA['dosage'].update({"status_rutaSNOMED": "inactivo"})
			else:
				responseMA['dosage'].update({"rutaSNOMED": 0})

		
			print('json resultado')
			print(responseMA)
			data = metodo+" y "+ruta

		else:
			responseMA ={"status": "json invalido"}
			responseMA1 = copy.deepcopy(responseMA)
			data=""
	if (recurso == 'diagnostico'):
		"""
		# recibir json de servidor
		params=""
		responseDia = generarRequest('https://stu3.test.pyrohealth.net/fhir/DiagnosticReport/24e3f407-1086-4ca1-bbe9-bcf920dba8b2')
		diagnostico = responseDia['conclusion']
		#-----
		"""
		with open("diagnostico.json", "r") as read_file:
			try:
				responseMA = json.load(read_file)
				responseMA1 = copy.deepcopy(responseMA)
				print("valido")
				isValid = True
			except ValueError as err:
				print("invalido")
				isValid = False
		if isValid:
			conclusion = responseMA['conclusion']
			descripciones = DescriptionS.objects.filter(term = conclusion) & DescriptionS.objects.filter(category_id = 6)
			sinonimos = Synonyms.objects.filter(term = conclusion)
			if descripciones:
				concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
				if concepto.active == '1':
					responseMA.update({"conclusionSNOMED": descripciones[0].conceptid})
					responseMA.update({"status_conclusionSNOMED": "activo"})
				else:
					responseMA.update({"conclusionSNOMED": descripciones[0].conceptid})
					responseMA.update({"status_conclusionSNOMED": "inactivo"})
			elif sinonimos:
				concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
				if concepto.active == '1':
					responseMA.update({"conclusionSNOMED": sinonimos[0].conceptid})
					responseMA.update({"status_conclusionSNOMED": "activo"})
				else:
					responseMA.update({"conclusionSNOMED": sinonimos[0].conceptid})
					responseMA.update({"status_conclusionSNOMED": "inactivo"})
			else:
				responseMA.update({"conclusionSNOMED": 0})
			print('json inicial')
			print(responseMA1)

			
			print('json resultado')
			print(responseMA)
			data = conclusion
		else:
			responseMA ={"status": "json invalido"}
			responseMA1 = copy.deepcopy(responseMA)
			data=""
	if (recurso == 'procedimiento'):
		"""
		# recibir json de servidor
		params=""
		responseDia = generarRequest('https://stu3.test.pyrohealth.net/fhir/DiagnosticReport/24e3f407-1086-4ca1-bbe9-bcf920dba8b2')
		diagnostico = responseDia['conclusion']
		#-----
		"""
		with open("procedimiento.json", "r") as read_file:
			try:
				responseMA = json.load(read_file)
				responseMA1 = copy.deepcopy(responseMA)
				print("valido")
				isValid = True
			except ValueError as err:
				print("invalido")
				isValid = False
		if isValid:
			for val in responseMA['note']:
				procedimiento = val['text']
				print(procedimiento)
				descripciones = DescriptionS.objects.filter(term = procedimiento) & DescriptionS.objects.filter(category_id = 4)
				sinonimos = Synonyms.objects.filter(term = procedimiento)
				if descripciones:
					concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
					if concepto.active == '1':
						val.update({"procedimentoSNOMED": descripciones[0].conceptid})
						val.update({"status_procedimentoSNOMED": "activo"})
					else:
						val.update({"procedimentoSNOMED": descripciones[0].conceptid})
						val.update({"status_procedimentoSNOMED": "inactivo"})

					#responseMA['note'].update({"procedimentoSNOMED": descripciones[0].conceptid})
				elif sinonimos:
					concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
					if concepto.active == "1":
						val.update({"procedimientoSNOMED": sinonimos[0].conceptid})
						val.update({"procedimientoSNOMED": "activo"})
					else:
						val.update({"procedimientoSNOMED": sinonimos[0].conceptid})
						val.update({"status_procedimientoSNOMED": "inactivo"})

				else:
					val.update({"procedimentoSNOMED": 0})
			print('json inicial')
			print(responseMA1)
				
			print('json resultado')
			print(responseMA)
			data = procedimiento
		else:
			responseMA ={"status": "json invalido"}
			responseMA1 = copy.deepcopy(responseMA)
			data=""

		#procedimiento = responseMA['note']['text']
	if (recurso == 'observacion'):
		"""
		# recibir json de servidor
		params=""
		responseOb = generarRequest('https://stu3.test.pyrohealth.net/fhir/Observation/9b59e305-270d-4c47-bfb6-b47683865c75')
		observacion = responseOb['code']['text']
		print(observacion)
		#-----
		"""
		with open("observacion.json", "r") as read_file:
			try:
				responseMA = json.load(read_file)
				responseMA1 = copy.deepcopy(responseMA)
				print("valido")
				isValid = True
			except ValueError as err:
				print("invalido")
				isValid = False
		if isValid:
		 	categoria = responseMA['category']
		 	descripciones = DescriptionS.objects.filter(term = categoria)
		 	sinonimos = Synonyms.objects.filter(term = categoria)
		 	if descripciones:
		 		concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
		 		if concepto.active == '1':
		 			responseMA.update({"categorySNOMED": descripciones[0].conceptid})
		 			responseMA.update({"status_categorySNOMED": "activo"})
		 		else:
		 			responseMA.update({"categorySNOMED": descripciones[0].conceptid})
		 			responseMA.update({"status_categorySNOMED": "inactivo"})
		 	elif sinonimos:
		 		concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
		 		if concepto.active == '1':
		 			responseMA.update({"categorySNOMED": sinonimos[0].conceptid})
		 			responseMA.update({"status_categorySNOMED": "activo"})
		 		else:
		 			responseMA.update({"categorySNOMED": sinonimos[0].conceptid})
		 			responseMA.update({"status_categorySNOMED": "inactivo"})
 
 			else:
 				responseMA.update({"categorySNOMED": 0})
 
 			code = responseMA['code']
	 		descripciones = DescriptionS.objects.filter(term = code)
	 		sinonimos = Synonyms.objects.filter(term = code)
	 		if descripciones:
	 			concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
	 			if concepto.active == '1':
	 				responseMA.update({"codeSNOMED": descripciones[0].conceptid})
	 				responseMA.update({"status_codeSNOMED": "activo"})
	 			else:
	 				responseMA.update({"codeSNOMED": descripciones[0].conceptid})
	 				responseMA.update({"status_codeSNOMED": "inactivo"})
	 		elif sinonimos:
	 			concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
	 			if concepto.active == '1':
	 				responseMA.update({"codeSNOMED": sinonimos[0].conceptid})
	 				responseMA.update({"codeSNOMED": "activo"})
	 			else:
	 				responseMA.update({"codeSNOMED": sinonimos[0].conceptid})
	 				responseMA.update({"codeSNOMED": "inactivo"})
 
 			else:
 				responseMA.update({"codeSNOMED": 0})
 			
 			data = categoria +" y "+ code
		else:
 			responseMA ={"status": "json invalido"}
		 	responseMA1 = copy.deepcopy(responseMA)
		 	data=""
	if (recurso == 'bundle'):

		 with open("bundle.json", "r") as read_file:
		 	try:
		 		responseMA = json.load(read_file)
		 		responseMA1 = copy.deepcopy(responseMA)
		 		print("valido")
		 		isValid = True
		 	except ValueError as err:
		 		print("invalido")
		 		isValid = False
		 if isValid:
			 for val in responseMA['entry']:
			 	#print("val")
			 	#print(val)

			 	if "Medication" == val['resource']['resourceType']:
			 		if 'code' in val['resource']:
			 			data = normalize(val['resource']['code'].encode("latin-1").decode("utf-8"))
				 		descripciones = DescriptionS.objects.filter(term = data) & DescriptionS.objects.filter(category_id = 10)
				 		sinonimos = Synonyms.objects.filter(term = data)
				 		if descripciones:
				 			concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
				 			if concepto.active == '1':
				 				val['resource'].update({"codeSNOMED": descripciones[0].conceptid})
				 				val['resource'].update({"status_codeSNOMED": "activo"})
				 			else:
				 				val['resource'].update({"codeSNOMED": descripciones[0].conceptid})
				 				val['resource'].update({"status_codeSNOMED": "inactivo"})
				 		elif sinonimos:
				 			concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
				 			if concepto.active == '1':
				 				val['resource'].update({"codeSNOMED": sinonimos[0].conceptid})
				 				val['resource'].update({"status_codeSNOMED": "activo"})
				 			else:
				 				val['resource'].update({"codeSNOMED": sinonimos[0].conceptid})
				 				val['resource'].update({"status_codeSNOMED": "inactivo"})
				 		else:
				 			val['resource'].update({"codeSNOMED": 0})
				 			existe = ConceptosNoEncontrados.objects.get(concepto = data)
				 			if not existe:
				 				ConceptosNoEncontrados.objects.Create(concepto = data)

			 	if "MedicationAdministration" == val['resource']['resourceType']:
			 		if 'dosage' in val['resource']:
				 		if 'method' in val['resource']['dosage']:
					 		metodo = normalize(val['resource']['dosage']['method'].encode("latin-1").decode("utf-8"))
			 				descripciones = DescriptionS.objects.filter(term = metodo) & DescriptionS.objects.filter(category_id = 8)
				 			sinonimos = Synonyms.objects.filter(term = metodo)
				 			if descripciones:
				 				concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
				 				if concepto.active == '1':
				 					val['resource']['dosage'].update({"methodSNOMED": descripciones[0].conceptid})
				 					val['resource']['dosage'].update({"status_methodSNOMED": "activo"})
				 				else:
				 					val['resource']['dosage'].update({"methodSNOMED": descripciones[0].conceptid})
				 					val['resource']['dosage'].update({"status_methodSNOMED": "inactivo"})
				 			elif sinonimos:
				 				concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
				 				if concepto.active == '1':
				 					val['resource']['dosage'].update({"methodSNOMED": sinonimos[0].conceptid})
				 					val['resource']['dosage'].update({"status_methodSNOMED": "activo"})
				 				else:
				 					val['resource']['dosage'].update({"methodSNOMED": sinonimos[0].conceptid})
				 					val['resource']['dosage'].update({"status_methodSNOMED": "inactivo"})
				 			else:
				 				val['resource']['dosage'].update({"metodoSNOMED": 0})
				 				existe = ConceptosNoEncontrados.objects.get(concepto = metodo)
				 			if not existe:
				 				ConceptosNoEncontrados.objects.create(concepto = metodo)

				 	if 'dosage' in val['resource']:
				 		if 'route' in val['resource']['dosage']:
				 			ruta = normalize(val['resource']['dosage']['route'].encode("latin-1").decode("utf-8"))
				 			descripciones = DescriptionS.objects.filter(term = ruta) & DescriptionS.objects.filter(category_id = 8)
				 			sinonimos = Synonyms.objects.filter(term = ruta)
				 			if descripciones:
				 				concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
				 				if concepto.active == '1':
				 					val['resource']['dosage'].update({"rutaSNOMED": descripciones[0].conceptid})
				 					val['resource']['dosage'].update({"status_rutaSNOMED": "activo"})
				 				else:
				 					val['resource']['dosage'].update({"rutaSNOMED": descripciones[0].conceptid})
				 					val['resource']['dosage'].update({"status_rutaSNOMED": "inactivo"})
			 
			 				elif sinonimos:
			 					concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
			 					if concepto.active == '1':
			 						val['resource']['dosage'].update({"rutaSNOMED": sinonimos[0].conceptid})
			 						val['resource']['dosage'].update({"status_rutaSNOMED": "activo"})
			 					else:
			 						val['resource']['dosage'].update({"rutaSNOMED": sinonimos[0].conceptid})
			 						val['resource']['dosage'].update({"status_rutaSNOMED": "inactivo"})
			 				else:
			 					val['resource']['dosage'].update({"rutaSNOMED": 0})
			 					existe = ConceptosNoEncontrados.objects.get(concepto = ruta)
				 			if not existe:
				 				ConceptosNoEncontrados.objects.Create(concepto = ruta)
			 	if "DiagnosticReport" == val['resource']['resourceType']:
			 		if 'conclusion' in val['resource']:
				 		conclusion = normalize(val['resource']['conclusion'].encode("latin-1").decode("utf-8"))
				 		descripciones = DescriptionS.objects.filter(term = conclusion) & DescriptionS.objects.filter(category_id = 6)
				 		sinonimos = Synonyms.objects.filter(term = conclusion)
				 		if descripciones:
				 			concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
				 			if concepto.active == '1':
				 				val['resource'].update({"conclusionSNOMED": descripciones[0].conceptid})
				 				val['resource'].update({"status_conclusionSNOMED": "activo"})
				 			else:
				 				val['resource'].update({"conclusionSNOMED": descripciones[0].conceptid})
				 				val['resource'].update({"status_conclusionSNOMED": "inactivo"})
				 		elif sinonimos:
				 			concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
				 			if concepto.active == '1':
				 				val['resource'].update({"conclusionSNOMED": sinonimos[0].conceptid})
				 				val['resource'].update({"status_conclusionSNOMED": "activo"})
				 			else:
				 				val['resource'].update({"conclusionSNOMED": sinonimos[0].conceptid})
				 				val['resource'].update({"status_conclusionSNOMED": "inactivo"})
				 		else:
				 			val['resource'].update({"conclusionSNOMED": 0})
				 			existe = ConceptosNoEncontrados.objects.get(concepto = conclusion)
				 			if not existe:
				 				ConceptosNoEncontrados.objects.Create(concepto = conclusion)
			 		

			 	if "Procedure" == val['resource']['resourceType']:
			 		if 'note' in val['resource']:
				 		for val1 in val['resource']['note']:
				 			procedimiento = normalize(val1['text'].encode("latin-1").decode("utf-8"))
				 			descripciones = DescriptionS.objects.filter(term = procedimiento) & DescriptionS.objects.filter(category_id = 4)
				 			sinonimos = Synonyms.objects.filter(term = procedimiento)
				 			if descripciones:
				 				concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
				 				if concepto.active == '1':
				 					val1.update({"procedimentoSNOMED": descripciones[0].conceptid})
				 					val1.update({"status_procedimentoSNOMED": "activo"})
				 				else:
				 					val1.update({"procedimentoSNOMED": descripciones[0].conceptid})
				 					val1.update({"status_procedimentoSNOMED": "inactivo"})
				 			elif sinonimos:
				 				concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
				 				if concepto.active == "1":
				 					val1.update({"procedimientoSNOMED": sinonimos[0].conceptid})
				 					val1.update({"procedimientoSNOMED": "activo"})
		 						else:
		 							val1.update({"procedimientoSNOMED": sinonimos[0].conceptid})
		 							val1.update({"status_procedimientoSNOMED": "inactivo"})
		 					else:
		 						val1.update({"procedimentoSNOMED": 0})
		 						existe = ConceptosNoEncontrados.objects.filter(concepto = procedimiento).first()
				 			if not existe:
				 				ConceptosNoEncontrados.objects.create(concepto = procedimiento)
			 	if "Observation" == val['resource']['resourceType']:
			 		if 'category' in val['resource']:
				 		categoria = normalize(val['resource']['category'].encode("latin-1").decode("utf-8"))
				 		descripciones = DescriptionS.objects.filter(term = categoria)
				 		sinonimos = Synonyms.objects.filter(term = categoria)
				 		if descripciones:
				 			concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
				 			if concepto.active == '1':
				 				val['resource'].update({"categorySNOMED": descripciones[0].conceptid})
				 				val['resource'].update({"status_categorySNOMED": "activo"})
				 			else:
				 				val['resource'].update({"categorySNOMED": descripciones[0].conceptid})
				 				val['resource'].update({"status_categorySNOMED": "inactivo"})
				 		elif sinonimos:
				 			concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
				 			if concepto.active == '1':
				 				val['resource'].update({"categorySNOMED": sinonimos[0].conceptid})
				 				val['resource'].update({"status_categorySNOMED": "activo"})
				 			else:
				 				val['resource'].update({"categorySNOMED": sinonimos[0].conceptid})
				 				val['resource'].update({"status_categorySNOMED": "inactivo"})

				 		else:
				 			val['resource'].update({"categorySNOMED": 0})
				 			existe = ConceptosNoEncontrados.objects.filter(concepto = categoria).first()
				 			if not existe:
				 				ConceptosNoEncontrados.objects.create(concepto = categoria)

			 		if 'code' in val['resource']:
				 		code = normalize(val['resource']['code'].encode("latin-1").decode("utf-8"))
				 		descripciones = DescriptionS.objects.filter(term = code)
				 		sinonimos = Synonyms.objects.filter(term = code)
				 		if descripciones:
				 			concepto = ConceptS.objects.get(id = descripciones[0].conceptid)
				 			if concepto.active == '1':
				 				val['resource'].update({"codeSNOMED": descripciones[0].conceptid})
				 				val['resource'].update({"status_codeSNOMED": "activo"})
				 			else:
				 				val['resource'].update({"codeSNOMED": descripciones[0].conceptid})
				 				val['resource'].update({"status_codeSNOMED": "inactivo"})
				 		elif sinonimos:
				 			concepto = ConceptS.objects.get(id = sinonimos[0].conceptid)
				 			if concepto.active == '1':
				 				val['resource'].update({"codeSNOMED": sinonimos[0].conceptid})
				 				val['resource'].update({"codeSNOMED": "activo"})
				 			else:
				 				val['resource'].update({"codeSNOMED": sinonimos[0].conceptid})
				 				val['resource'].update({"codeSNOMED": "inactivo"})
		 				else:
		 					val['resource'].update({"codeSNOMED": 0})
		 					existe = ConceptosNoEncontrados.objects.get(concepto = code)
				 			if not existe:
				 				ConceptosNoEncontrados.objects.Create(concepto = code)

			 data=""
		 else:
		 	responseMA ={"status": "json invalido"}
		 	responseMA1 = copy.deepcopy(responseMA)
		 	data=""
		# categoria = responseMA['category']
		
		# descripciones = DescriptionS.objects.filter(term = categoria)
		# sinonimos = Synonyms.objects.filter(term = categoria)
		# if descripciones:
		# 	responseMA.update({"categorySNOMED": descripciones[0].conceptid})
		# elif sinonimos:
		# 	responseMA.update({"categorySNOMED": sinonimos[0].conceptid})
		# else:
		# 	responseMA.update({"categorySNOMED": 0})

		# code = responseMA['code']
		# descripciones = DescriptionS.objects.filter(term = code)
		# sinonimos = Synonyms.objects.filter(term = code)
		# if descripciones:
		# 	responseMA.update({"codeSNOMED": descripciones[0].conceptid})
		# elif sinonimos:
		# 	responseMA.update({"codeSNOMED": sinonimos[0].conceptid})
		# else:
		# 	responseMA.update({"codeSNOMED": 0})
		# print('json inicial')
		# print(responseMA1)
		
		# print('json resultado')
		# print(responseMA)
		# data = categoria +" y "+ code
	return render(request, 'Aplicacion1/index.html')
	#return render(request, 'Aplicacion1/index.html', {'json1':responseMA1, 'json2':responseMA})
	#return render(request, 'Aplicacion1/index.html', {'json1':responseMA1, 'json2':responseMA, 'data': data})


