from django.db import models

class TokensDiagnosticos(models.Model):
    #id = models.CharField(max_length=36, primary_key=True)
    token = models.CharField(max_length=255)
    id_descripcion = models.CharField(max_length=255)
    largo_palabras_termino = models.IntegerField()
# Create your models here.
