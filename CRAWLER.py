# -*- coding: utf-8 -*-
"""
https://github.com/safteinzz/WebCrawler

@author: SaFteiNZz
"""
# =============================================================================
#         ~DOC
#
#            https://docs.python.org/3/library/concurrent.futures.html
#            https://realpython.com/intro-to-python-threading/#starting-a-thread
#            https://www.tutorialsteacher.com/python/public-private-protected-modifiers
#            https://docs.python.org/3/library/urllib.parse.html
#            https://docs.python.org/3/library/queue.html
#            https://stackoverflow.com/questions/9371114/check-if-list-of-objects-contain-an-object-with-a-certain-attribute-value/9371143#9371143
#            https://doc.qt.io/archives/qt-4.8/qspinbox.html
#
# =============================================================================
#         ~CONSTANTES
# =============================================================================

ICOENLACE = 'safteinzz.ico'
GUIENLACE = 'interfazCrawling.ui'

# =============================================================================
#         ~IMPORTS
# =============================================================================
#Relacionado con el scrapping
import requests, re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

#Datasets y models
from pandasmodel import PandasModel
import pandas as pd

#Relacionado con concurrencia
import time 
from queue import Queue, Empty

#Concurrencia
from qtpy.QtCore import Signal
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

# --- Interfaz
#Lanzamiento
import sys
#Ventana
from PyQt5 import uic
#Messagebox
import ctypes
#PyQT5
from PyQt5 import QtGui
#Widgets pyQT5
from PyQt5.QtWidgets import QFileDialog, QMainWindow, QApplication
#Importar interfaz
Ui_MainWindow, QtBaseClass = uic.loadUiType(GUIENLACE)

# =============================================================================
#         ~FUNCIONES PUBLICAS
# =============================================================================
# ~Funcion alertas messagebox
#
#            @text comentario del messagebox
#            @title titulo ventana messagebox
#            @style (INT) tipo de ventana
#                  0 : OK
#                  1 : OK | Cancel
#                  2 : Abort | Retry | Ignore
#                  3 : Yes | No | Cancel
#                  4 : Yes | No
#                  5 : Retry | No 
#                  6 : Cancel | Try Again | Continue
#            
# =============================================================================
def Messagebox(text, title, style):
    return ctypes.windll.user32.MessageBoxW(0, text, title, style)  

# =============================================================================
# ~Seleccionar Ruta de fichero/carpeta   
#
#    @filtro => Sera el tipo de extension
#    @titulo  => Titulo de la ventana
#    @guardar => Booleano para saber si se quiere cargar o guardar
#    - 1 = guardar
#    - 0 = cargar
#    @carpetas => Booleano para saber si se quiere carpetas o archivos
#    - 1 = carpetas
#    - 0 = ficheros
#    Ejemplo filtro: "xls(*.xls);;csv(*.csv)"  
#
# ============================================================================= 
def seleccionarFichero(filtro, titulo, guardar, carpetas):
    qFD = QFileDialog()
    if carpetas == 1:
        return QFileDialog.getExistingDirectory(qFD, titulo, "", QFileDialog.ShowDirsOnly)
    else:        
        if guardar == 0:                   
            return QFileDialog.getOpenFileName(qFD, titulo, "",filtro)
        elif guardar == 1:
            return QFileDialog.getSaveFileName(qFD, titulo, "",filtro)



# -----------------------------------------------------------------------------
# ~Clase enlace
# =============================================================================
class Enlace:
    def __init__(self, url, texto):
        self.url = url
        self.texto = texto

# -----------------------------------------------------------------------------
# ~Clase Crawler 
# =============================================================================
class CrawlerConcurrente:
    def __init__(self, url_scrap, termino):
        urlParsed = urlparse(url_scrap)
        self.parametro_url = "{}://{}".format(urlParsed.scheme, urlParsed.netloc)
        self.aBuscar = termino 
        self.enlacesEncontrados = [] #Lista de coincidencias
        self.colaCrawl = Queue(20)
        self.workers = ThreadPoolExecutor(max_workers=8)
        enlace = Enlace(self.parametro_url, "Parametro a buscar")
        self.colaCrawl.put(enlace)
        
    def BuscarCoincidencias(self, html):
#        Guardar html y buscar el termino en cualquier lado
        soup = BeautifulSoup(html, 'html.parser')
        links = soup.find_all('a',text=re.compile("\w*" + self.aBuscar + "\w*", re.UNICODE))
        for link in links:            
            url = link['href']
#            Quitar espacios en blanco de derecha e izquierda
            texto = link.get_text().strip()            
#            Formar url
            if url.startswith('/'): url = urljoin(self.parametro_url, url)            
#            Guardar enlace y meter en cola
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
                   
    def runCC(this, self):  #this es CC, self es mainClass
#        print("Buscando el termino '" + this.aBuscar + "' en " + this.parametro_url)  #debug
        done = False
#        Resetear index para limpiar busquedas pasadas
        self.model.df = self.model.df.iloc[0:0]
        while not done:            
            try:
#                Sacar enlace de la cola
                enlace = this.colaCrawl.get(timeout=5)         
#                Comprobar paths de las urls, no podemos comprobar urls ya que podrian tener netlocs diferentes con paths iguales
                if any(urlparse(x.url).path == urlparse(enlace.url).path for x in this.enlacesEncontrados): continue              
            
#                Meter en el dataframe del tableview en enlace
                if len(this.enlacesEncontrados) > 0:                 
                    df = pd.DataFrame([[enlace.texto,enlace.url]], columns=('Enlace', 'URL'))
                    self.updateProgress.emit(df)
                
#                Meter enlace a la cola de enlaces vistados
                this.enlacesEncontrados.append(enlace)
                
#                Scrap workers
                worker = this.workers.submit(this.scrapWeb, enlace.url)
                worker.add_done_callback(this.scrapeCallback)
                time.sleep(0.5)
                
#                Limitar coincidencias
                if self.ui.cBLimitarCoincidencias.isChecked():
                    if len(this.enlacesEncontrados) - 1 == self.ui.sBCoincidencias.value():
                        raise Empty()
                    
            except Empty:
                self.ui.lEstadoActual.setText('Busqueda finalizada')
                done = True                
                return
            
            except Exception as e:
                print(e)
                continue
            
# -----------------------------------------------------------------------------
# ~Clase ventana
# =============================================================================
class mainClass(QMainWindow):
    
#    Signal para hacer updates en tiempo real al dataframe del tableview
    updateProgress = Signal(pd.DataFrame)
    
    def __init__(self):
        super(mainClass, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self) 
        self.setWindowIcon(QtGui.QIcon(ICOENLACE))
        
        df = pd.DataFrame(columns=('Enlace', 'URL'))    
        self.model = PandasModel(df)
        self.ui.tVResultado.setModel(self.model)
        self.ui.tVResultado.setColumnWidth(0, 400)
        self.ui.tVResultado.horizontalHeader().setStretchLastSection(True)
        self.updateProgress.connect(self.model.add)
        
# 
#         ~Eventos links
# =============================================================================
        
# ---------- Botones
        #Boton Buscar
        self.ui.pBBuscar.clicked.connect(self.pBBuscarClicked)
        #Boton Exportar
        self.ui.pBExportar.clicked.connect(self.pBExportarClicked)  

# ---------- Otros 
        #Line edit URL
        self.ui.tETermino.mousePressEvent = self.tETerminoClicked
        #Line edit URL
        self.ui.tEURLPagina.mousePressEvent = self.tEURLPaginaClicked 
        #Checkbox coincidencias
        self.ui.cBLimitarCoincidencias.stateChanged.connect(self.cBLimitarCoincidenciasChanged)

        
# 
# ~Funciones eventos
# =============================================================================
#     ~Evento Buscar coincidencias  
# =============================================================================
    def pBBuscarClicked( self ):
        termino = self.ui.tETermino.toPlainText()
        url = self.ui.tEURLPagina.toPlainText()
        cc = CrawlerConcurrente(url,termino)
        self.ui.lEstadoActual.setText('Buscando...')
        mainWorker = Thread(target=cc.runCC, args=(self, ))
        mainWorker.start()
        
# =============================================================================
#     ~Evento Exportar coincidencias  
# =============================================================================
    def pBExportarClicked( self ):
        rutaGuardado = seleccionarFichero("txt(*.txt);;csv(*.csv)", "Seleccionar donde guardar fichero", 1, 0)
        if rutaGuardado[1] == 'csv(*.csv)':
            self.model.df.to_csv(rutaGuardado[0], header = True,index = False, encoding='utf-8') 
        else:
            dfModel = self.model.df
            with open(rutaGuardado[0], 'a') as f:
                f.write(
                    dfModel.to_string(header = True,index = False)
                )
        self.ui.lEstadoActual.setText('Exportado')
            
              
        
# =============================================================================
#     ~Evento checkbox limitar coincidencias 
# =============================================================================       
    def cBLimitarCoincidenciasChanged( self ):
        if self.ui.sBCoincidencias.isEnabled(): self.ui.sBCoincidencias.setDisabled(True)
        else: self.ui.sBCoincidencias.setEnabled(True)
        
# =============================================================================
#     ~Eventos limpiar textedits onclick  (se tiene que poder mandar el widget como argumento y no duplicamos codigo)
# =============================================================================
    def tEURLPaginaClicked(self, event):
        self.ui.tEURLPagina.setText('')
        self.ui.tEURLPagina.setTextColor(QtGui.QColor(0,0,0))
        
    def tETerminoClicked(self, event):
        self.ui.tETermino.setText('')
        self.ui.tETermino.setTextColor(QtGui.QColor(0,0,0))
#   
# RUNUP
# =============================================================================
# *Función MAIN
###############################################################################
def main():
    app = QApplication(sys.argv)
    window = mainClass()
    window.show()
    app.exec_()
# *Ejecucion ------------------------------------------------------------------
if __name__ == '__main__':
    main()   
#------------------------------------------------------------------------------