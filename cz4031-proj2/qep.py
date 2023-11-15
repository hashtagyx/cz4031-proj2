import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout
from plotly.graph_objs import FigureWidget
# from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5 import QtCore, QtWidgets, QtWebEngineWidgets
import plotly.graph_objects as go
import numpy as np
import igraph
from igraph import Graph, EdgeSeq
import json

def QEP(query):
# check for attributes and add to graph as node attributes if present
  qep_attrs=['Relation Name','Hash Cond', 'Merge Cond', 'Join Type','Shared Hit Blocks','Filter', 'Rows Removed by Filter']

  def add_attr(ptr, g, attrs):
    # if 'Scan' in attrs['Node Type']:
    #   g.vs[ptr]['name'] = '\N{GREEK SMALL LETTER SIGMA}'+attrs['Filter']
    # else:
    g.vs[ptr]['name'] = attrs['Node Type']
    for attr in qep_attrs:
      if attr in attrs:
        g.vs[ptr][attr] = attrs[attr]


  result_data = query['explain_result'][0]
  g= Graph()
  g.add_vertex()
  add_attr(0, g, result_data['Plan'])


  ptr = 0 #ptr to current id

  if 'Plans' in result_data['Plan']:
      temp_result = [(0, result_data['Plan']['Plans'])] #list of tuples (parent id, plan)
      while len(temp_result)>0: # temp_result is a list
          parent, loop_result = temp_result.pop(0)
          for p in loop_result[:]: # p is a dict
              ptr+=1
              g.add_vertex()
              g.add_edge(ptr, parent) #manually add edge
              add_attr(ptr, g, p) #add attributes for the

              if 'Plans' in p:
                  temp_result.append((ptr, p['Plans']))
  print(g)

  labels=list(g.vs['name'])
  N = len(labels)
  E=[e.tuple for e in g.es]
  layt = g.layout('rt', root=[0])
  Xn=[layt[k][0] for k in range(N)]
  Yn=[layt[k][1] for k in range(N)]
  Xe=[]
  Ye=[]
  for e in E:
      Xe+=[layt[e[0]][0],layt[e[1]][0], None]
      Ye+=[layt[e[0]][1],layt[e[1]][1], None]
  print("in the tea",g.vs)
  hoverlabels = []
  for i in range(N):
    # hoverlabel = 'Name: ' + labels[i]
    hoverlabel = ''
    for j in qep_attrs:
      try:
        if g.vs[i][j] is not None:
          hoverlabel = hoverlabel + '<br>' +  j + ': ' + str(g.vs[i][j])
        if j == 'Shared Hit Blocks':
          blocks = int(g.vs[i][j])
          print(blocks)
          block_size = 8192
          hoverlabel = hoverlabel + '<br>' + 'Total num of blocks hit in Bytes: ' + str(block_size * blocks)
          # print(hoverlabel)
      except:
        continue
    hoverlabels.append(hoverlabel)
    print("IN THE LOOP", hoverlabels)

  fig = go.Figure()
  fig.add_trace(go.Scatter(x=Xe,
                    y=Ye,
                    mode='lines',
                    line=dict(color='rgb(210,210,210)', width=1),
                    hoverinfo='none'
                    ))
  fig.add_trace(go.Scatter(x=Xn,
                    y=Yn,
                    mode='markers+text',
                    name='',
                    marker=dict(symbol='line-ew',
                                  size=18,
                                  color='#6175c1',    #'#DB4551',
                                  line=dict(color='#ffffff', width=1)
                                  ),
                    text=labels,
                    textposition='middle center',
                    hoverinfo='text',
                    customdata = np.stack(hoverlabels, axis =-1),
                    hovertemplate="%{customdata}",
                    opacity=0.8
                    ))

  fig.update_layout(
      showlegend=True,
      hovermode="closest",
      margin=dict(b=0, l=0, r=0, t=0),
      xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
      yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, autorange="reversed"),
  )
  return fig
# PyQt5 code to display the Plotly figure in a QWidget
# from plotly.graph_objs import FigureWidget
# from PyQt5.QtWebEngineWidgets import QWebEngineView
# from PyQt5.QtWidgets import QVBoxLayout

class Widget(QtWidgets.QWidget):
    def __init__(self, fig, parent=None):
        super().__init__(parent)
        self.button = QtWidgets.QPushButton('Plot', self)
        self.browser = QtWebEngineWidgets.QWebEngineView(self)

        vlayout = QtWidgets.QVBoxLayout(self)
        vlayout.addWidget(self.button, alignment=QtCore.Qt.AlignHCenter)
        vlayout.addWidget(self.browser)

        self.button.clicked.connect(self.show_graph)
        self.resize(1000,800)
        self.fig = fig

    def show_graph(self):
        # Create a new QDialog for the pop-up window
        pop_up_dialog = QtWidgets.QDialog(self)
        pop_up_dialog.setWindowTitle('Query Execution Plan')
        pop_up_dialog.resize(700,500)

        # Embed a QWebEngineView for the figure in the pop-up dialog
        pop_up_browser = QtWebEngineWidgets.QWebEngineView(pop_up_dialog)
        pop_up_browser.setHtml(self.fig.to_html(include_plotlyjs='cdn'))

        # Set layout for the pop-up dialog
        layout = QtWidgets.QVBoxLayout(pop_up_dialog)
        layout.addWidget(pop_up_browser)

        # Show the pop-up dialog
        pop_up_dialog.exec_()
        # self.browser.setHtml(fig.to_html(include_plotlyjs='cdn'))

if __name__ == "__main__":
  with open('query.txt') as f:
    query = f.read()
    # print(contents)
  query = json.loads(query)
  figure = QEP(query)
  app = QtWidgets.QApplication([])
  widget = Widget(figure)
  widget.show()
  app.exec()