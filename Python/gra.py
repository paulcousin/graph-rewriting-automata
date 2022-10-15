################################ REQUIRED PACKAGES ################################
import math
import numpy as np

import igraph as ig

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' # removes unnecessary outputs from TensorFlow
import tensorflow as tf


################################ Graph CLASS ################################
class Graph:
   
    #--------------- INITIALIZATION METHOD ---------------#
    def __init__(self, adjacency_matrix, state_vector):
        # checks the format of the inputs and acts accordingly to create two properly formated attributes
        if tf.is_tensor(adjacency_matrix): # if adjacency_matrix is a tensor
            self.adjacency_matrix = adjacency_matrix
        else: # if adjacency_matrix is not a tensor
            self.adjacency_matrix = tf.sparse.from_dense(tf.constant(adjacency_matrix, dtype=tf.int32))
        if tf.is_tensor(state_vector): # if state_vector is a tensor
            self.state_vector = state_vector
        else: # if state_vector is not a tensor
            self.state_vector = tf.constant(state_vector, dtype=tf.int32)

    #--------------- UTILITIES ---------------#
    def order(self):
        return self.adjacency_matrix.dense_shape.numpy()[1]
    
    def clone(self):
        return Graph(self.adjacency_matrix, self.state_vector)

    def isomorphic(self, g2):
        g1 = self
        ig1 = self.igraph()
        ig2 = g2.igraph()

        isomorphisms = ig1.get_isomorphisms_vf2(ig2)
        state_vector = g1.state_vector.numpy()
        test = g2.state_vector.numpy()

        for i in range(len(isomorphisms)):
            for j in range(len(isomorphisms[i])):
                test[j] = g2.state_vector.numpy()[isomorphisms[i][j]]
            if (test == state_vector).all(): 
                return True
        
        return False

    #--------------- GRAPH PLOT ---------------#
    def plot(self):
        edgelist = np.asarray([list(d) for d in self.adjacency_matrix.indices.numpy()], dtype= np.int32) # TO SIMPLIFY LATER
        g = ig.Graph(n=self.order(), edges=edgelist).simplify()
        visual_style = {}
        visual_style["vertex_size"] = 4
        visual_style["layout"] = g.layout_kamada_kawai(maxiter=10*self.order())
        visual_style["vertex_color"] = ["purple" if self.state_vector.numpy()[d][0]==1 else "orange" for d in range(self.order())]
        return ig.plot(g, bbox=(20*math.sqrt(self.order()), 20*math.sqrt(self.order())), margin=10, **visual_style)

    #--------------- EVOLUTION METHOD ---------------#
    def evolve(self, rule):
        new = rule.evolve(self)
        self.adjacency_matrix = new.adjacency_matrix
        self.state_vector = new.state_vector

    #--------------- EXPORTS ---------------#
    def mathematica(self):
        aM = "SparseArray[{"+','.join([str(list(d))+"->1" for d in self.adjacency_matrix.indices.numpy()+1]).replace('[','{').replace(']','}')+"},{"+','.join([str(d) for d in self.adjacency_matrix.dense_shape.numpy()])+"}]"
        sV = "{"+','.join([str(d) for d in self.state_vector.numpy()]).replace('[','{').replace(']','}')+"}"
        return "{"+aM+","+sV+"}"
        
    def igraph(self):
        edgelist = np.asarray([list(d) for d in self.adjacency_matrix.indices.numpy()], dtype= np.int32) # TO SIMPLIFY LATER
        g = ig.Graph(n=self.order(), edges=edgelist).simplify()
        g.vs["size"] = 4
        g.vs["color"] = ["purple" if self.state_vector.numpy()[d][0]==1 else "orange" for d in range(self.order())]
        return g


################################ Rule CLASS ################################
class Rule:
    """
    The Rule class can be instantiated with:
     * the degree of the d-regular graph it must be applied to
     * a rule number
    """

    #--------------- INITIALIZATION METHOD ---------------#
    def __init__(self, degree, number):
        if 0 <= int(number) < 4**(2*(int(degree)+1)) and int(degree) > 0:
            self.degree = int(degree)
            self.number = int(number)
        else:
            raise TypeError('Invalid input.')
    
    #--------------- UTILITIES ---------------#
    def binary_digits(self):
        # creates a list with the 4*(d+1) first binary digits of the rule number
        rule = [int(x) for x in np.binary_repr(self.number)]
        rule.reverse()
        for i in range(len(rule), 4*(self.degree+1)): rule.append(0)
        return rule[::-1]

    #--------------- EVOLUTION METHODS ---------------#
    def evolve(self, graph):
        adjacency_matrix = graph.adjacency_matrix
        state_vector = graph.state_vector

        # checks the compatibility of the graph
        if not tf.math.reduce_all(tf.equal(tf.sparse.sparse_dense_matmul(adjacency_matrix, tf.transpose([tf.ones(graph.order(), dtype=tf.int32)])),self.degree*tf.transpose([tf.ones(graph.order(), dtype=tf.int32)]))):
            raise TypeError('The provided graph is not a ' + str(self.degree) + '-regular graph, the rule cannot be applied.')

        # computes the configuration vector
        configurations = tf.sparse.sparse_dense_matmul(adjacency_matrix, state_vector).numpy().transpose().squeeze() + 4*state_vector.numpy().transpose().squeeze()

        # importing the list of binary digits
        rule = self.binary_digits()[::-1]

        # computes an updated state vector and a division vector
        new_state_vector = [rule[c] for c in configurations]
        division_vector =  [rule[c+2*(self.degree+1)] for c in configurations]

        while 1 in division_vector:
            i = division_vector.index(1)
            dim = len(division_vector)

            # updates the state vector
            for j in range(self.degree-1):
                new_state_vector.insert(i, new_state_vector[i])

            # updates the division vector
            division_vector[i]=0
            for j in range(self.degree-1):
                division_vector.insert(i, 0)

            # updates the adjacency matrix
            line_indices = tf.sparse.slice(adjacency_matrix, [i,0], [1,dim]).indices.numpy()[:,1]
            new_lines = tf.SparseTensor(indices=[[0,line_indices[0]]], values=[1], dense_shape=[self.degree,dim])
            for k in range(1, self.degree):
                new_lines = tf.sparse.add(new_lines, tf.SparseTensor(indices=[[k,line_indices[k]]], values=[1], dense_shape=[self.degree,dim]))
            adjacency_matrix = tf.sparse.concat(0,
                [
                    tf.sparse.slice(adjacency_matrix, [0,0], [i,dim]),
                    new_lines,
                    tf.sparse.slice(adjacency_matrix, [i+1,0], [dim-i-1,dim])
                ]
            )
            column_indices = tf.sparse.slice(adjacency_matrix, [0,i], [dim+(self.degree-1),1]).indices.numpy()[:,0]
            new_columns = tf.SparseTensor(indices=[[column_indices[0],0]], values=[1], dense_shape=[dim+(self.degree-1),self.degree])
            for k in range(1, self.degree):
                new_columns = tf.sparse.add(new_columns, tf.SparseTensor(indices=[[column_indices[k],k]], values=[1], dense_shape=[dim+(self.degree-1),self.degree]))
            adjacency_matrix = tf.sparse.concat(1,
                [
                    tf.sparse.slice(adjacency_matrix, [0,0], [dim+(self.degree-1),i]),
                    new_columns,
                    tf.sparse.slice(adjacency_matrix, [0,i+1], [dim+(self.degree-1),dim-i-1])
                ]
            )
            
            # adding the junction submatrix
            adjacency_matrix = tf.sparse.add(adjacency_matrix, tf.SparseTensor(indices=np.array([[m,n] for m,n in np.ndindex((self.degree,self.degree)) if m!=n])+i, values=[1 for n in range(self.degree*(self.degree-1))], dense_shape=[dim+(self.degree-1), dim+(self.degree-1)]))

        # updates the state vector
        state_vector = tf.convert_to_tensor(np.array([new_state_vector]).T, dtype=tf.int32)

        return Graph(adjacency_matrix, state_vector)

    def jump(self, graph, n):
        for i in range(n):
            graph = self.evolve(graph)
        return graph

    #--------------- RULE PLOT ---------------#
    def plot(self):
        # importing the list of binary digits
        rule = self.binary_digits()[::-1]

        # figure initialization
        fig, ax = plt.subplots()
        
        # layout
        sx, sy = 40, 20 # spacing
        vr = 1 # vertex radius
        el = 6 # edge length
        dst = 3.4*el # distance between config and result
        scale = 10 # output scale

        for c in range(2*self.degree+2):
            # translation
            tx = sx*(c-(self.degree+1)*(c//(self.degree+1)))
            ty = 18 if c<self.degree+1 else 0

            # adds central vertex
            x, y = tx, ty
            circle = plt.Circle((x,y), vr, facecolor='purple' if c<self.degree+1 else 'orange', edgecolor='black')
            ax.add_patch(circle) # configuration
            if rule[4*self.degree+3-c]==0: # result without division
                circle = plt.Circle((x+dst,y), vr, facecolor='purple' if rule[2*self.degree+1-c]==1 else 'orange', edgecolor='black')
                ax.add_patch(circle)
            else: # result with division
                for k in range(self.degree):
                    x, y = tx+el*np.cos(-np.pi/2+(k*2*np.pi)/self.degree), ty+el*np.sin(-np.pi/2+(k*2*np.pi)/self.degree)
                    circle = plt.Circle(((tx+x)/2+dst,(ty+y)/2), vr, facecolor='purple' if rule[2*self.degree+1-c]==1 else 'orange', edgecolor='black')
                    ax.add_patch(circle)
                    for l in range(k):
                        x_, y_ = tx+el*np.cos(-np.pi/2+(l*2*np.pi)/self.degree), ty+el*np.sin(-np.pi/2+(l*2*np.pi)/self.degree)
                        line = plt.Line2D([(tx+x)/2+dst, (tx+x_)/2+dst], [(ty+y)/2, (ty+y_)/2], color='black', zorder=-1)
                        ax.add_line(line)  

            # adds arrow
            x, y = tx+el+2*vr, ty  # start
            dx, dy = dst-2*(el+2*vr), 0 # end
            width = 3
            arrow = mpatches.Arrow(x, y, dx, dy, width, facecolor='black')
            ax.add_patch(arrow)

            # adds edges and outer vertices one-by-one
            for k in range(self.degree):
                color = 'orange' if k<(c-(self.degree+1)*(c//(self.degree+1))) else 'purple'
                x, y = tx+el*np.cos(-np.pi/2+(k*2*np.pi)/self.degree), ty+el*np.sin(-np.pi/2+(k*2*np.pi)/self.degree)
                # initial configuration
                line = plt.Line2D([tx,x], [ty, y], color='black', zorder=-1)
                circle = plt.Circle((x,y), vr, facecolor=color, edgecolor='black')
                ax.add_line(line)
                ax.add_patch(circle)
                # result at t+1
                if rule[4*self.degree+3-c]==0: # undivided
                    line = plt.Line2D([tx+dst,x+dst], [ty, y], color='black', zorder=-1)
                    ax.add_line(line)
                else: # divided
                    line = plt.Line2D([(tx+x)/2+dst,x+dst], [(ty+y)/2, y], color='black', zorder=-1)
                    ax.add_line(line)

        plt.axis('equal') # scale x and y equaly
        plt.axis('off') # don't display axes
        fig.set_size_inches(scale*self.degree, scale)
        plt.show()