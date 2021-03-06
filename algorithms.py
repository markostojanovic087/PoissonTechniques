# -*- coding: utf-8 -*-
"""
Created on Sat Oct 22 02:03:59 2016

@author: Marko
"""
import numpy as np
import sys
from constants import *
from scipy.sparse import lil_matrix
from proba_mtg import multigridPoissonSolveA

def poissonSolve(inputSpace, idm, N, precision):
    if idm == FFT_ID:
        return fftPoissonSolve(inputSpace, N, precision)
    elif idm == JCB_ID:
        return jacobiPoissonSolve(inputSpace, N, precision)
    elif idm == GS_ID:
        return gsPoissonSolve(inputSpace, N, precision)
    elif idm == SOR_ID:
        return sorPoissonSolve(inputSpace, N, precision)
    elif idm == MTG_ID:
        return multigridPoissonSolveA(inputSpace, N, precision)
    else:
        return inputSpace

def initA(dim, dense=0):
    No = dim ** 3
    if dense == 0:
        A = lil_matrix((No,No))
    else:
        print('Dense')
        A = np.zeros((No,)*2)
    for i in range(0,No):
        ci = i  // dim**2
        cj = (i - ci * dim**2) // dim
        ck = i  %  dim
        curr = (ci * dim + cj) * dim +ck
        A[i,curr] = 6
        
        v = ck - 1
        if v>=0:       
            curr = (ci * dim + cj) * dim + v
            A[i,curr] = -1 
    
        v = ck + 1
        if v<dim:       
            curr = (ci * dim + cj) * dim + v
            A[i,curr] = -1 
            
        v = cj - 1
        if v>=0:       
            curr = (ci * dim + v) * dim + ck
            A[i,curr] = -1
        
        v = cj + 1
        if v<dim:
            curr = (ci * dim + v) * dim + ck
            A[i,curr] = -1
        
        v = ci - 1
        if v>=0:       
            curr = (v * dim + cj) * dim + ck
            A[i,curr] = -1
        
        v = ci + 1
        if v<dim:       
            curr = (v * dim + cj) * dim + ck
            A[i,curr] = -1
            
    return A

def calculateError(A, x, b):
    error = A.dot(x) - b
    Signal = np.sum(x ** 2)
    Noise = np.sum(error ** 2)
    SNR = (10 * np.log10(Signal / Noise))  
    maxerr = np.max(np.abs(error))
    minerr = np.min(np.abs(error))
    avgerr = np.average(np.abs(error))

    print(" | SNR: ", SNR, (' Test Passed' if SNR>69.0 else ' Test Failed'), end="")    
    print(' | Max error: ', maxerr, end="")
    print(' | Min error: ', minerr, end="")
    print(' | Average error: ', avgerr, end="")    
    return error

def dst(x,axis=-1):
    """Discrete Sine Transform (DST-I)

    Implemented using 2(N+1)-point FFT
    xsym = r_[0,x,0,-x[::-1]]
    DST = (-imag(fft(xsym))/2)[1:(N+1)]

    adjusted to work over an arbitrary axis for entire n-dim array
    """
    n = len(x.shape)
    N = x.shape[axis]
    slices = [None]*3
    for k in range(3):
        slices[k] = []
        for j in range(n):
            slices[k].append(slice(None))
    newshape = list(x.shape)
    newshape[axis] = 2*(N+1)
    xsym = np.zeros(newshape,np.float)
    slices[0][axis] = slice(1,N+1)
    slices[1][axis] = slice(N+2,None)
    slices[2][axis] = slice(None,None,-1)
    for k in range(3):
        slices[k] = tuple(slices[k])
    xsym[slices[0]] = x
    xsym[slices[1]] = -x[slices[2]]
    DST = np.fft.fft(xsym,axis=axis)
    #print xtilde
    return (-(DST.imag)/2)[slices[0]]

def dst3(x,axes=(-1,-2,-3)):
    return dst(dst(dst(x,axis=axes[0]),axis=axes[1]),axis=axes[2])

def idst3(x,axes=(-1,-2,-3)):
    n = x.shape[0]
    u = dst(dst(dst(x,axis=axes[0]),axis=axes[1]),axis=axes[2])
    u= u * (2/(n+1))**2			#normalize ,change for rectangular domain
    return u

def fftPoissonSolve(inputSpace, N, precision):    
    print(' | FFT', end="")
    sys.stdout.flush()

    imag = np.zeros((N,)*3)
    inputSpace = inputSpace + 1j * imag
    
    #print('INPUT= ', inputSpace[][][])
    #outputSpace = inputSpace
    outputSpace = np.fft.fftn(inputSpace)
    #outputSpace = dst3(inputSpace)
    #print(outputSpace.shape)
    #print('FFT= ', outputSpace)
    h = 1.0 / N    
    w = np.exp(2 * np.pi * 1j / N)
    wi = 1.0
    wj = 1.0
    wk = 1.0      

    #processLater = []    
    
    for i in range(0,N):
        for j in range(0,N):
            for k in range(0,N):
                denom = wi + 1.0/wi + wj + 1.0/wj + wk + 1.0/wk - 6
                if not denom == 0:
                    outputSpace[i][j][k] = outputSpace[i][j][k] * h * h / denom
                    #if outputSpace[i][j][k].real < 0:
                        #print('** [',i,'][',j,'][',k,']')
                else:
                    outputSpace[i][j][k] = 0
                    #print('[',i,'][',j,'][',k,']')
                    #processLater.append([i,j,k]) 
                wk = wk * w
            wj = wj * w
        wi = wi * w                

    #interpolate(processLater, outputSpace, N)    
    #print('POISS= ', outputSpace)
    outputSpace =  np.fft.ifftn(outputSpace)
    #outputSpace =  idst3(outputSpace)
    #print('OUTPUT= ', outputSpace)
    
    return outputSpace.real
    
def jacobiPoissonSolve(f, N, precision):
    print(' | Jacobi', end="")
    sys.stdout.flush()

    iter_limit = 1000
    h = 1.0/N   
    
    x  = np.zeros((N,)*3)    
    it_count = 0
    for it_count in range(iter_limit):
        x_new = np.zeros_like(x)
        
        for i in range (0,N):
            for j in range (0,N):
                for k in range (0,N):
                    prevI = 0 if i==0   else x[i-1][j][k]
                    pastI = 0 if i==N-1 else x[i+1][j][k]
                    prevJ = 0 if j==0   else x[i][j-1][k]
                    pastJ = 0 if j==N-1 else x[i][j+1][k]
                    prevK = 0 if k==0   else x[i][j][k-1]
                    pastK = 0 if k==N-1 else x[i][j][k+1]
                    x_new[i][j][k] = (prevI + pastI + prevJ + pastJ + prevK + pastK - h * h * f[i][j][k] )/6
         
        if np.allclose(x, x_new, atol=precision):
            break
        x = x_new
        
    print(' | Iterations: ', it_count+1, end="")
    return x  

def gsPoissonSolve(f, N, precision):
    print(' | Gauss-Seidel', end="")
    sys.stdout.flush()

    iter_limit = 1000
    h = 1.0/N   
    
    x  = np.zeros((N,)*3)    
    it_count = 0
    for it_count in range(iter_limit):
        x_new = np.zeros_like(x)
        
        for i in range (0,N):
            for j in range (0,N):
                for k in range (0,N):
                    prevI = 0 if i==0   else x_new[i-1][j][k]
                    pastI = 0 if i==N-1 else x[i+1][j][k]
                    prevJ = 0 if j==0   else x_new[i][j-1][k]
                    pastJ = 0 if j==N-1 else x[i][j+1][k]
                    prevK = 0 if k==0   else x_new[i][j][k-1]
                    pastK = 0 if k==N-1 else x[i][j][k+1]
                    x_new[i][j][k] = (prevI + pastI + prevJ + pastJ + prevK + pastK - h * h * f[i][j][k] )/6
         
        if np.allclose(x, x_new, atol=precision):
            break
        x = x_new
        
    print(' | Iterations: ', it_count+1, end="")
    return x

def sorPoissonSolve(f, N, precision):
    print(' | SOR', end="")
    sys.stdout.flush()

    iter_limit = 1000
    h = 1.0/N
    w = 2.0 / (1 + np.pi / N)      
    
    x  = np.zeros((N,)*3)    
    it_count = 0
    for it_count in range(iter_limit):
        x_new = np.zeros_like(x)
        
        for i in range (0,N):
            for j in range (0,N):
                for k in range (0,N):
                    curr = x[i][j][k]
                    prevI = 0 if i==0   else x_new[i-1][j][k]
                    pastI = 0 if i==N-1 else x[i+1][j][k]
                    prevJ = 0 if j==0   else x_new[i][j-1][k]
                    pastJ = 0 if j==N-1 else x[i][j+1][k]
                    prevK = 0 if k==0   else x_new[i][j][k-1]
                    pastK = 0 if k==N-1 else x[i][j][k+1]
                    fsor = ((1-w)*curr)
                    x_new[i][j][k] = fsor + w*(prevI + pastI + prevJ + pastJ + prevK + pastK - h * h * f[i][j][k] )/6
         
        if np.allclose(x, x_new, atol=precision):
            break
        x = x_new
        
    print(' | Iterations: ', it_count+1, end="")
    return x

def multigridPoissonSolve(f, N, precision):
    print(' | Multigrid', end="")
    sys.stdout.flush()
    
    h = 1.0 / N
    
    f = f.reshape((N**3))
    A = initA(N,1)
    b = - h**2 * f
    
    x = np.zeros(N**3) # initial guess
    for it_count in range(100):
        r = b - A.dot(x)
        diff = np.linalg.norm(r)/np.linalg.norm(b)
        if diff < precision:
            break
        du = vcycle(A,r,h)
        x += du
        print ("step %d, rel error=%e"% (it_count+1, diff ))
    print(' | Iterations: ', it_count+1, end="")

    return x.reshape((N, N, N))

def gsIteration(outputS, inputS, sizeF, h):
    power2 = np.log2(sizeF)
    case = power2 % 3

    if case != 0:
        exp = ( power2 + 3 - case ) / 3
        N = int(pow(2,exp))
        
        if case == 1:
            M = int(N / 2)
        else:
            M = int(N)
        
        L = int(N / 2)
    
    else:
        exp = power2 / 3
        N = M = L = int(pow(2,exp))
           
    outputS = outputS.reshape((N,M,L))
    inputS = inputS.reshape((N,M,L))
    for i in range (0,N):
        for j in range (0,M):
            for k in range (0,L):
                prevI = 0 if i==0   else outputS[i-1][j][k]
                pastI = 0 if i==N-1 else outputS[i+1][j][k]
                prevJ = 0 if j==0   else outputS[i][j-1][k]
                pastJ = 0 if j==M-1 else outputS[i][j+1][k]
                prevK = 0 if k==0   else outputS[i][j][k-1]
                pastK = 0 if k==L-1 else outputS[i][j][k+1]
                outputS[i][j][k] = (prevI + pastI + prevJ + pastJ + prevK + pastK - h * h * inputS[i][j][k] )/6
    
    return outputS.reshape((sizeF))

def gs1DIteration(outputS, inputS, sizeF, h, A): #NE VALJA - Cim se zavrsi prvi v-cycle ovo gresi jer ne menja hasdkodovano A (susedi su drugaciji skroz...)
    power2 = np.log2(sizeF)
    case = power2 % 3

    va = np.empty_like(outputS)
    va[:] = outputS
    
    if case != 0:
        exp = ( power2 + 3 - case ) / 3
        N = int(pow(2,exp))
        
        if case == 1:
            M = int(N / 2)
        else:
            M = int(N)
        
        L = int(N / 2)
    else:
        exp = power2 / 3
        N = M = L = int(pow(2,exp))
    
    #print('sizeF=',sizeF,' N=',N,'   M=',M,'   L=',L)
    for i in range(0,sizeF):
        #print('A[',i,'][in]=', np.nonzero(A[i]))
        #print('A[',i,'][nz]= ',A[i][np.nonzero(A[i])])
        ci = i  // (M * L)
        #cj = (i % ( M * L)) // L        
        cj = (i - ci * M * L) // L
        ck = i % L
        
        #if (L == 8 and M==16):
         #   print('i=', i,' ci=',ci,'   cj=',cj,'   ck=',ck)
        #curr = (ci * N + cj) * M +ck
        
        v = ck - 1
        prevK = outputS[((ci * M + cj) * L + v if v>=0 else 0)]
    
        v = ck + 1
        pastK = outputS[((ci * M + cj) * L + v if v<L  else 0)]
        
        v = cj - 1
        prevJ = outputS[((ci * M + v) * L + ck if v>=0 else 0)]
    
        v = cj + 1
        pastJ = outputS[((ci * M + v) * L + ck if v<M  else 0)]
        
        v = ci - 1
        prevI = outputS[((v * M + cj) * L + ck if v>=0 else 0)]
    
        v = ci + 1
        pastI = outputS[((v * M + cj) * L + ck if v<N  else 0)]
    
        #outputS[i] = (prevI + pastI + prevJ + pastJ + prevK + pastK - h * h * inputS[i])/6
        s1a = -prevI - prevJ - prevK
        s2a = -pastI - pastJ - pastK
        outputS[i] = (inputS[i] - s1a - s2a)/6
        print('---- I= ', i,' ------ sizeF= ', sizeF,'-----------')
        print('s1a = ', s1a)
        print('s2a = ', s2a)
        print('outputS = ',outputS[i])
        
        s1 = np.dot(A[i, :i], va[:i])
        s2 = np.dot(A[i, i + 1:], va[i + 1:])
        print('s1 = ', s1)
        print('s2 = ', s2)
        va[i] = (inputS[i] - s1 - s2) / A[i,i];

        print('va = ',va[i])
    input("Press Enter to continue...")
    return outputS

#def smooth(v, f, sizeF, h):
    #for k in range(sizeF):
     #   s1 = np.dot(A[k, :k], v[:k])
     #   s2 = np.dot(A[k, k + 1:], v[k + 1:])
     #   v[k] = (f[k] - s1 - s2) / A[k,k];

def vcycle(A,f,h):
    # perform one v-cycle on the matrix A
    sizeF = np.size(A,axis=0);

    # size for direct inversion < 15
    if sizeF == 1:
        v = np.linalg.solve(A,f)        
        return v    
    
    # N1=number of Gauss-Seidel iterations before coarsening
    N1 = 5;
    v = np.zeros(sizeF);
    for numGS in range(N1):
        gs1DIteration(v, f, sizeF, h, A)
        #for k in range(sizeF):
         #   s1 = np.dot(A[k, :k], v[:k])
          #  s2 = np.dot(A[k, k + 1:], v[k + 1:])
           # v[k] = (f[k] - s1 - s2) / A[k,k];
            
    # construct interpolation operator from next coarser to this mesh
    # next coarser has (n/2) points
    sizeC = (int)(sizeF/2)
    P = np.zeros((sizeF,sizeC));
    for k in range(sizeC):
        P[2*k,k] = 1; # copy these points
    for k in range(sizeC-1):
        P[2*k+1,k] = .5; # average these points
        P[2*k+1,k+1] = .5;
    
    # compute residual
    residual = f - A.dot(v)
    
    # project residual onto coarser mesh
    residC = np.dot(P.transpose(),residual)
    
    # Find coarser matrix (sizeC X sizeC)
    AC = np.dot(P.transpose(),A.dot(P))
    vC = vcycle(AC,residC,h);

    # extend to this mesh
    v = np.dot(P,vC)

    # N2=number of Gauss-Seidel iterations after coarsening
    N2 = 5;
    for numGS in range(N2):
        gs1DIteration(v, f, sizeF, h,A)
        #for k in range(sizeF):
         #   s1 = np.dot(A[k, :k], v[:k])
          #  s2 = np.dot(A[k, k + 1:], v[k + 1:])
           # v[k] = (f[k] - s1 - s2) / A[k,k];
        
    return v
 
def interpolate(processLater, outputSpace, N):
    for p in range(0,len(processLater)):
        elem = processLater[p]
        i = elem[0]
        j = elem[1]
        k = elem[2]
        
        cnt = 0
        csum = 0
        
        for n in range (np.max([0,i-1]),np.min([N-1,i+1])+1):
            for m in range (np.max([0,j-1]),np.min([N-1,j+1])+1):
                for l in range (np.max([0,k-1]),np.min([N-1,k+1])+1):
                    if not (i==n and j==m and k==l):
                        cnt += 1
                        csum += outputSpace[n][m][l]
                        
        outputSpace[i][j][k] = csum / cnt