import matplotlib.pyplot as plt
import numpy as np
import scipy.misc
import glob
import sys
import random #new

from helpers import *

# you shouldn't need to make any more imports

class NeuralNetwork(object):
    """
    Abstraction of neural network.
    Stores parameters, activations, cached values.
    Provides necessary functions for training and prediction.
    """
    def __init__(self, layer_dimensions, drop_prob=0.0, reg_lambda_1=0.0, reg_lambda_2=0.0,
                 activation=None, optimizer=None):
        """
        Initializes the weights and biases for each layer
        :param layer_dimensions: (list) number of nodes in each layer
        :param drop_prob: drop probability for dropout layers. Only required in part 2 of the assignment
        :param reg_lambda: regularization parameter. Only required in part 2 of the assignment
        """
        seed = 1
        np.random.seed(seed)

        self.parameters = {}
        self.num_layers = len(layer_dimensions)
        self.drop_prob = drop_prob
        self.reg_lambda_1 = reg_lambda_1
        self.reg_lambda_2 = reg_lambda_2
        self.activation = activation
        self.relu_v = np.vectorize(self.relu)
        self.relud_v = np.vectorize(self.relu_derivative)

        self.optimizer = optimizer
        self.last_dW_momz  = [0.0] * self.num_layers
        self.last_db_momz = [0.0] * self.num_layers
        self.last_dW_momz_m = [0.0] * self.num_layers
        self.last_dW_momz_v = [0.0] * self.num_layers

        #idx is the index of val - 1, because idx starts at zero, despite enumerating starting
        #at layer_dimensions[1:]. So idx points to the previous layer.
        self.parameters['weights'] = [.1*np.random.randn(layer_dimensions[idx], val)
            for idx, val in enumerate(layer_dimensions[1:])]

        self.parameters['biases'] = [0 for n in layer_dimensions[1:]]

    def affineForward(self, A, W, b):
        """
        Forward pass for the affine layer.
        :param A: input matrix, shape (L, S), where L is the number of hidden units in the previous layer and S is
        the number of samples
        :returns: the affine product WA + b, along with the cache required for the backward pass
        """
        #or maybe join b into W

        Z = np.dot(W.T,A) + b
        cache = (A,W,b,Z)

        return Z, cache

    def activationForward(self, A, activation="relu"):
        """
        Common interface to access all activation functions.
        :param A: input to the activation function
        :param prob: activation funciton to apply to A. Just "relu" for this assignment.
        :returns: activation(A)
        """
        if self.activation is not None:
            return self.activation(A)

        return self.relu_v(A)

    def relu(self, X):
        return np.maximum(0,X)

    def dropout(self, A, prob):
        """
        :param A:
        :param prob: drop prob
        :returns: tuple (A, M)
            WHERE
            A is matrix after applying dropout
            M is dropout mask, used in the backward pass
        """
        M = np.random.rand(A.shape[0],A.shape[1])
        M = (M > prob) * 1.0
        M /= (1 - prob)
        A *= M
        return A, M

    def forwardPropagation(self, X):
        """
        Runs an input X through the neural network to compute activations
        for all layers. Returns the output computed at the last layer along
        with the cache required for backpropagation.
        :returns: (tuple) AL, cache
            WHERE
            AL is activation of last layer
            cache is cached values for each layer that
                     are needed in further steps
        """
        #### cache = (A,W,b,Z,M) ####

        cache = []
        A = X
        W = self.parameters['weights']
        b = self.parameters['biases']

        # range(0, 3) = (0, 1, 2)
        # two fewer computation than layers (last cycle will be softmax)
        for l in range(0, self.num_layers - 2):
            Z, c1 = self.affineForward(A, W[l], b[l])
            A = self.activationForward(Z)
            A, M = self.dropout(A,self.drop_prob)
            c = (c1[0],c1[1],c1[2],c1[3],M)
            cache.append(c)

        #last affine
        Z, c = self.affineForward(A, W[self.num_layers-2], b[self.num_layers-2])
        cache.append(c)

        #softmax
        Z = Z - np.max(Z, axis=0)
        Zx = np.exp(Z)
        AL = Zx / np.sum(Zx, axis = 0)
#         AL = np.exp(Z) / np.sum(np.exps(Z), axis = 0)

        # never predict less than 0.01% chance
        AL = np.maximum(AL, .00001)
        AL = AL / np.sum(AL, axis = 0)

        return AL, cache

    def costFunction(self, AL, y):
        """
        :param AL: Activation of last layer, shape (num_classes, S)
        :param y: labels, shape (S)
        :param alpha: regularization parameter
        :returns cost, dAL: A scalar denoting cost and the gradient of cost
        """

        predictions = np.argmax(AL, axis=0)
        correct = np.sum(predictions == y)
        accuracy = correct / float(len(y))

        W = self.parameters['weights']
        b = self.parameters['biases']

        # compute loss
        cost = 0
        for j, sample in enumerate(AL.T):
            #if label = node #, then yTrue = 1
            for i, node in enumerate(sample):
                yTrue = 1 if y[j] == i else 0
                cost += -yTrue*np.log(sample[i])
            #L1 Regularization
            if self.reg_lambda_1 > 0:
              for r in range(self.num_layers - 1):
                cost += self.reg_lambda_1 * np.sum(np.abs(W[r]))
                cost += self.reg_lambda_1 * np.sum(np.abs(b[r]))
            #L2 Regularization
            if self.reg_lambda_2 > 0:
              for r in range(self.num_layers - 1):
                cost += self.reg_lambda_2 * np.sum(np.multiply(W[r], W[r]))
                cost += self.reg_lambda_2 * np.sum(np.multiply(b[r], b[r]))
        cost /= AL.shape[1]

        # gradient of cost #just subtract 1 from the correct class

        dAL = AL
        for j in range(0, AL.shape[1]): #cols - samples
            for i in range(0, AL.shape[0]): #rows - nodes
                yTrue = 1 if y[j] == i else 0
                dAL[i,j] -= yTrue

        #dAL[i,j] /= AL.shape[1]

        #average over all samples - DONT DO
        #dAL = AL.sum(axis=1)/AL.shape(1)

        return accuracy, cost, dAL

    def affineBackward(self, dA_prev, cache):
        """
        Backward pass for the affine layer.
        :param dA_prev: gradient from the next layer.
        :param cache: cache returned in affineForward
        :returns dA: gradient on the input to this layer
                 dW: gradient on the weights
                 db: gradient on the bias
        """
        g_prime = self.relud_v

        A, W, b, Z_r = cache[0], cache[1], cache[2], cache[3]

        dA = np.dot(W,dA_prev)
        dW = np.dot(dA_prev,A.T)
        db = np.sum(g_prime(0.0, Z_r), axis=1, keepdims=True)

        if self.reg_lambda_1 > 0:
          dW += self.reg_lambda_1 * np.sign(W.T)
          if type(b) != 'int':
            db = db + ( self.reg_lambda_1 * np.sign(b))

        if self.reg_lambda_2 > 0:
          dW += self.reg_lambda_2 * 2.0 * W.T
          if type(b) != 'int':
            db = db + (self.reg_lambda_2 * 2.0 * b)

        return dA, dW, db

    def activationBackward(self, dA, cache, activation="relu"):
        """
        Interface to call backward on activation functions.
        In this case, it's just relu.
        """
        pass


    def relu_derivative(self, dx, cached_x):
        #don't need param: dx
        dx = 1 if cached_x >= 0 else 0
        return dx

    def dropout_backward(self, dA, cache):
        return dA * cache

    def backPropagation(self, dAL, Y, cache):
        """
        Run backpropagation to compute gradients on all paramters in the model
        :param dAL: gradient on the last layer of the network. Returned by the cost function.
        :param Y: labels
        :param cache: cached values during forwardprop
        :returns gradients: dW and db for each weight/bias
        """

        """
        Key math:
        Setting from notes:
        Use r instead of l for layer
        Z^r = (W^r)^T * A^(r-1) = affine layer
        A^r = g^r(Z^r) = activated layer
        W^r : layer r-1 -> layer r
        g^r is probably relu, but you can add a g^final = softmax step

        Problem: given dL/dA^r, compute dL/A^r and DL/dW^r. We only need to return
        dL/dW^r, bu computing dL/dA^r enables recursion.

        Implement this update:
        Temp: Z^r = g(A^(r-1))
        Set: dL/dA^(r-1) = (W^r)^T * dL/dA^r * g'(Z^r) (note g' not g)
        Set: dL/dW^r = dL/dA^r * g'(Z^r) * (A^(r-1)^)T (note g' not g)

        """
        #gradients = []
        gradients = {}

        g_prime = self.relud_v

        #hopefully list length is correct
        gradients['dW'] = [0] * (self.num_layers - 1)
        gradients['db'] = [0] * (self.num_layers - 1)

        dL_dA_rprev = dAL
        dL_dA_rprev, dL_dW_r, dL_db_r = self.affineBackward(dL_dA_rprev, cache[self.num_layers - 2])
        gradients['dW'][self.num_layers - 2] = dL_dW_r
        gradients['db'][self.num_layers - 2] = dL_db_r
        # start with last layer, note that range(3,-1,-1) == (3, 2, 1, 0)
        for r in range(self.num_layers - 3, -1, -1):
            if self.drop_prob > 0:
                dL_dA_rprev = self.dropout_backward (dL_dA_rprev, cache[r][4])
            dL_dA_rprev *= g_prime(0,cache[r][3])
            dL_dA_rprev, dL_dW_r, dL_db_r = self.affineBackward(dL_dA_rprev, cache[r])

            gradients['dW'][r] = dL_dW_r
            gradients['db'][r] = dL_db_r

        return gradients


    def updateParameters(self, gradients, alpha):
        """
        :param gradients: gradients for each weight/bias
        :param alpha: step size for gradient descent
        """
        EPSILON = .0000001
        beta=.9
        beta1=0
        beta2=0
        W = self.parameters['weights']
        b = self.parameters['biases']

        # momentum
        # z^{k+1} = \beta z^k + grad f(w^k)
        # w^{k+1} = w^k - \alpha z^{k+1}

        #assuming gradients have been averaged across samples already

        if self.optimizer == None:
            for i,dW in enumerate(gradients['dW']):
                deltaW = dW * alpha
                self.parameters['weights'][i] -= deltaW.transpose()
            for i,db in enumerate(gradients['db']):
                deltab = db * alpha
                self.parameters['biases'][i] -= deltab

        elif self.optimizer == "sgd_momentum":
            for i, dW in enumerate(gradients['dW']):
                self.last_dW_momz[i] = beta * self.last_dW_momz[i] + (1 - beta) * dW
                W[i] -= alpha * self.last_dW_momz[i].T

            for i, db in enumerate(gradients['db']):
                self.last_db_momz[i] = beta * self.last_db_momz[i] + (1 - beta) * db
                b[i] -= alpha * self.last_db_momz[i]

        elif self.optimizer == "rms_prop":

            for i, dW in enumerate(gradients['dW']):
                self.last_dW_momz[i] = beta * self.last_dW_momz[i] + (1 - beta) * dW**2
                W[i] -= alpha * dW / np.sqrt(self.last_dW_momz[i] + EPSILON)

            for i, db in enumerate(gradients['db']):
                self.last_db_momz[i] = beta * self.last_db_momz[i] + (1 - beta) * db**2
                b[i] -= alpha * db / np.sqrt(self.last_db_momz[i] + EPSILON)

        elif self.optimizer == "adam":
            for i, dW in enumerate(gradients['dW']):
                self.last_dW_momz_m[i] = beta1 * self.last_dW_momz_m[i] + (1 - beta1) * dW
                self.last_dW_momz_v[i] = beta2 * self.last_dW_momz_v[i] + (1 - beta2) * dW**2
                x -= (alpha * self.last_dW_momz_m[i] / (np.sqrt(self.last_dW_momz_v[i]) + EPSILON)).T
            
            for i, db in enumerate(gradients['db']):
                self.last_db_momz_m[i] = beta1 * self.last_db_momz_m[i] + (1 - beta1) * db
                self.last_db_momz_v[i] = beta2 * self.last_db_momz_v[i] + (1 - beta2) * db**2
                x -= alpha * self.last_db_momz_m[i] / (np.sqrt(self.last_db_momz_v[i]) + EPSILON)
        

    def train(self, X, y, iters=10000, alpha=0.0001, batch_size=200, print_every=100): #2000
        """
        :param X: input samples, each column is a sample
        :param y: labels for input samples, y.shape[0] must equal X.shape[1]
        :param iters: number of training iterations
        :param alpha: step size for gradient descent
        :param batch_size: number of samples in a minibatch
        :param print_every: no. of iterations to print debug info after
        """
        import datetime
        currentDT = datetime.datetime.now()
        print (currentDT.strftime("%I:%M:%S %p"))
        
        X, Xv, y, yv = self.split_data(X,y)
        
        costs = 0
        accuracies = 0 
        for i in range(0, iters):
            # get minibatch
            X_batch, y_batch = self.get_batch(X, y, batch_size)
            # forward prop
            AL, cache = self.forwardPropagation(X_batch)
            # compute loss
            accuracy, cost, dAL = self.costFunction(AL, y_batch)
            # compute gradients
            gradients = self.backPropagation(dAL, y_batch, cache)
            # update weights and biases based on gradient
            self.updateParameters(gradients, alpha)
            
            costs += cost
            accuracies += accuracy
            if i % print_every == 0:
                ALv, cachev = self.predict(Xv)
                accuracyv, costv, dALv = self.costFunction(ALv, yv)
                cost_avg = costs if i == 0 else (costs / float(print_every))
                accuracy_avg = accuracies if i == 0 else (accuracies / float(print_every))
                print("[%d / %d] Cost: %.4f, Acc: %.1f%% || CostV: %.4f, AccV: %.1f%%, Alpha: %.5f" % (i, iters, cost, 100 * accuracy, costv, 100 * accuracyv, alpha))
                
                if alpha >= .00001:
                    alpha *= .82
                costs = 0
                accuracies = 0
                # print cost, train and validation set accuracies

    def predict(self, X):
        """print("[%d / %d] Cost: %.4f, Accuracy: %.1f%%" % (i, iters, cost, 100 * accuracy))
        Make predictions for each sample
        """
        return self.forwardPropagation(X)

    def get_batch(self, X, y, batch_size):
        """
        Return minibatch of samples and labels

        :param X, y: samples and corresponding labels
        :parma batch_size: minibatch size
        :returns: (tuple) X_batch, y_batch
        """

        sample = random.sample(range(X.shape[1]), batch_size)

        #Assuming X and y are numpy arrays
        X_batch = X[:,sample]
        y_batch = y[sample]

        return X_batch,y_batch

    def split_data(self, X, y, percent_valid=.1):
        num_samples = X.shape[1]
        split = int(num_samples*percent_valid)
        X_valid = X[:,0:split]
        X_train = X[:,split:num_samples]
        y_valid = y[0:split]
        y_train = y[split:num_samples]
        return X_train, X_valid, y_train, y_valid
