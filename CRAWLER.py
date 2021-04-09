# -*- coding: utf-8 -*-
"""
Created on Wed Mar 31 21:03:12 2021

@author: SaFteiNZz
"""
#Documentación relevante
#https://docs.python.org/3/library/concurrent.futures.html
#https://realpython.com/intro-to-python-threading/#starting-a-thread
#https://www.tutorialsteacher.com/python/public-private-protected-modifiers
#https://docs.python.org/3/library/urllib.parse.html
#https://docs.python.org/3/library/queue.html
#https://stackoverflow.com/questions/9371114/check-if-list-of-objects-contain-an-object-with-a-certain-attribute-value/9371143#9371143


#Imports
from bs4 import BeautifulSoup
import time, requests, re
from queue import Queue, Empty
#from threading import Thread
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse
 
class Enlace:
    def __init__(self, url, texto):
        self.url = url
        self.texto = texto

class CrawlerConcurrente:
    def __init__(self, url_scrap, termino):
        urlParsed = urlparse(url_scrap)
        self.parametro_url = '{}://{}'.format(urlParsed.scheme, urlParsed.netloc)
        self.aBuscar = termino
        self.enlacesEncontrados = [] #Lista de coincidencias
        
        self.colaCrawl = Queue(20)
        self.workers = ThreadPoolExecutor(max_workers=8)
        
        enlace = Enlace(self.parametro_url, "Parametro a buscar")
        self.colaCrawl.put(enlace)
        
    def BuscarCoincidencias(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        links = soup.find_all('a',text=re.compile("\w*" + self.aBuscar + "\w*", re.UNICODE))
        for link in links:            
            url = link['href']
            texto = link.get_text().strip()
            if url.startswith('/'): url = urljoin(self.parametro_url, url)
            if any(x.url == url for x in self.enlacesEncontrados): return
            enlace = Enlace(url,texto)
            self.colaCrawl.put(enlace)            
        
    def scrapWeb(self, url):
        try:
            res = requests.get(url, timeout=(3, 30))
            return res
        except requests.RequestException:
            return
        
    def scrapeCallback(self, res):
        result = res.result()
        if result and result.status_code == 200:
            self.BuscarCoincidencias(result.text)
                   
    def runCC(self):
        outFile = open("Coincidencias.txt","w")
        print("Buscando el termino '" + self.aBuscar + "' en " + self.parametro_url)
        done = False
        while not done:
            try:
                enlace = self.colaCrawl.get(timeout=5)                
                if any(x.url == enlace.url for x in self.enlacesEncontrados): continue 
            
                if len(self.enlacesEncontrados) == 0:
                    outputText = "Resultados de la busqueda del termino '" + self.aBuscar + "' en la pagina " + self.parametro_url + ":\n\n\n"
                else:
                    outputText = "Coincidencia nº " + str(len(self.enlacesEncontrados)) + "\nTexto: " + enlace.texto +"\nURL: " + enlace.url + "\n\n"
                    print(outputText)
                
                outFile.write(outputText)
                self.enlacesEncontrados.append(enlace)
                
#                workers
                worker = self.workers.submit(self.scrapWeb, enlace.url)
                worker.add_done_callback(self.scrapeCallback)
                time.sleep(0.5)  
                    
            except Empty:
                print("Busqueda completada")
                done = True
                return
            
            except Exception as e:
                print(e)
                continue
        
#        Cerrar fichero cuando termine cola 
        outFile.close()
        
    
        
if __name__ == '__main__':
    cc = CrawlerConcurrente("https://www.elpais.com/", "vacuna")
#    cc = CrawlerConcurrente("https://www.20minutos.es/", "vacuna")
    cc.runCC()