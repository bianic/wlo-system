import numpy as np
import random
import matplotlib.pyplot as plt
import time
import json

class optimizer:
    def __init__(self,objec_func,n_iterations,n_init_points,search_space,SGD_learn_rate,batch_size) -> None:
        self.object_func    = objec_func                            # set objective function
        self.n_init_points  = n_init_points                         # set the start points
        self.search_space   = search_space                          # set the search space
        self.dim            = len(search_space)                     # set the dimension of points
        self.quantile       = 0.2                                   # set the quantile to divide the points
        self.set_sigma()                                            # set the standard deviation of GMM
        self.SGD_learn_rate = SGD_learn_rate                        # set the learning rate for SGD when selecting next point
        self.SGD_iteration  = 20                                    # set the number of iterations for SGD when selecting next point
        self.SGD_h          = 0.01                                  # set the range to calculate the gradient in SGD
        self.gmm_max        = 1/(self.sigma * np.sqrt(2 * np.pi))   # calculate the theoretical maximum of the GMM
        self.explore_bound  = np.exp(-0.09*(self.dim-0.5)**1.4)     # set the boundary for exploration
        self.ex_bound_coe   = 1/n_iterations/10                     # coefficient for the boundary
        self.batch_size     = batch_size                            # set the batch size in the batch mode
        self.n_iterations   = round(n_iterations/batch_size)        # calculate the number of iterations in batch mode
        self.best           = np.array([])                          # collect best objective values during runtime
    def set_sigma(self):
        # calculate the standard deviation by the maximum length in the search space
        difference_ss   = self.search_space[:,1]-self.search_space[:,0]
        self.sigma      = np.max(difference_ss)/8

    def init_point(self,n_points:int) -> np.array:
        # generate n start points randomly within the search space
        init_points = np.zeros((n_points,len(self.search_space)),dtype=int)
        for i in range(n_points):
            init_points[i][:] = [random.randint(self.search_space[dim][0],self.search_space[dim][1]) for dim in range(len(self.search_space))]
        return init_points
    
    def sort_observations(self):
        # sort the points according to the objective value and collect best objective value
        sorted_order    = sorted(range(len(self.observations)), key=lambda k: self.observations[k])
        n_lx            = int(np.ceil(len(sorted_order)*self.quantile))
        self.lx         = self.points[sorted_order[0:n_lx-1]][:]
        self.gx         = self.points[sorted_order[n_lx:]][:]
        self.best       = np.append(self.best,self.observations[sorted_order[0]])

    def calculate_standard_gmm(self,distance:np.array) -> float:
        # calculate the value of the GMM for the distance matrix of the point
        temp_prob = 1/(self.sigma * np.sqrt(2 * np.pi)) * np.exp(-1/2 * (distance/self.sigma) **2)
        return temp_prob
    def detect_lx_dense(self, point:np.array) -> float:
        # calculate the density of the one point by its the weighted GMM value, to determine if next point is exploration
        len_lx = len(self.lx)
        weight_lx = np.array([(len_lx-i)*2/(len_lx+1)/len_lx for i in range(len_lx)],dtype=float)
        distance_lx = [np.sqrt(np.sum((point - self.lx[i,:])**2)) for i in range(len_lx)]
        lx          = self.calculate_standard_gmm(np.array(distance_lx))
        lx          = np.sum(lx*weight_lx)
        return lx
    def acquisition_func(self, point:np.array) -> float:
        # calculate the distance in l(x)
        len_lx = len(self.lx)
        weight_lx = np.array([(len_lx-i)*2/(len_lx+1)/len_lx for i in range(len_lx)],dtype=float)
        distance_lx = [np.sqrt(np.sum((point - self.lx[i,:])**2)) for i in range(len_lx)]
        lx          = self.calculate_standard_gmm(np.array(distance_lx))
        lx          = np.sum(lx*weight_lx)  
        len_gx = len(self.gx)
        distance_gx = [np.sqrt(np.sum((point - self.gx[len_gx-i-1][:])**2)) for i in range(len_gx)]
        gx          = self.calculate_standard_gmm(np.array(distance_gx))
        gx          = np.sum(gx)/len_gx
        
        return np.log((lx+1e-8)/(gx+1e-8))
    def detect_alias(self, input_point: np.array, point_ref: np.array) -> bool:
        # detect if the point has been explored
        for current_point in point_ref:
            if np.array_equal(input_point, current_point):
                return 1
        return 0 
    def SGD_gradient(self,x: np.array, h: float):
        # calculate the gradient at the point
        grad = np.zeros_like(x,dtype=float)
        for dimension in range(len(x)):
            new_point_1,new_point_2 = x.copy(),x.copy()
            new_point_1,new_point_2 = new_point_1.astype(float),new_point_2.astype(float)
            new_point_1[dimension] -= h/2.0
            new_point_2[dimension] += h/2.0
            grad[dimension] = (self.acquisition_func(new_point_2)-self.acquisition_func(new_point_1))/h
        return grad
    def SGD(self,init_point):
        # SGD process, find the maximum of the acquisition function
        current_point = init_point
        current_point = current_point.astype(float)
        previous_update = np.zeros_like(current_point)
        for i in range(self.SGD_iteration):
            grad = self.SGD_gradient(x=current_point,h=self.SGD_h)
            update = np.array(self.SGD_learn_rate * grad,dtype=float)
            current_point += np.sign(update)*np.log(np.abs(update)+1)
            # detect if the point outside the range
            for j in range(len(current_point[0,:])):
                if current_point[0,j] < self.search_space[j,0]:
                    current_point[0,j] = self.search_space[j,0]
                elif current_point[0,j] > self.search_space[j,1]:
                    current_point[0,j] = self.search_space[j,1]  
                else:
                    current_point[0,j]
            # collect the intermidiate points that will be used when the point is detected alias
            if i==0:
                self.previous_point_buffer = np.array(current_point,dtype=int)
            elif not(self.detect_alias(np.array(current_point,dtype=int),self.points)):
                repeat = not(np.array_equal(np.array(current_point.flatten(),dtype=int),self.previous_point_buffer[-1]))
                if repeat:
                    self.previous_point_buffer = np.append(self.previous_point_buffer,np.array(current_point,dtype=int),axis=0)

            if np.array_equal(np.round(previous_update,4),np.round(update,4)):
                break

            previous_update = update

        return current_point
    def SGD_explore_exploit(self):
        # select next point and determine if it should be exploration
        w_best = np.exp(-1/len(self.points)**0.2)
        len_lx = len(self.lx)
        weight_lx = np.array([1/len_lx for i in range(len_lx)],dtype=float)

        point_lx = np.array([self.lx[i,:]*weight_lx[i] for i in range(len_lx)])
        for i in range(20):
            init_point = (1-w_best) * self.init_point(1) +  (w_best) * np.sum(point_lx,axis=0)
            af_new = self.acquisition_func(init_point)
            if i == 0:
                candi = init_point.copy()
                af_old = af_new
            elif af_old < af_new:
                af_old = af_new
                candi = init_point.copy()

        init_point = candi
        current_point = self.SGD(init_point=init_point)
        max_lx = self.detect_lx_dense(current_point)
        threshold = self.gmm_max*self.explore_bound*np.exp(-(self.ex_bound_coe*(len_lx-0.99))**0.3)
        ## for batch mode:
        batch_point = np.full((self.batch_size, self.dim), None)

        # compare the threshold
        if max_lx < threshold:
            w_best = 0
            for i in self.previous_point_buffer:
                if self.detect_alias(current_point.astype(int),self.points):
                    random_move = np.array([random.randint(-1,1) for _ in range(self.dim)])
                    current_point = current_point + random_move
                else:
                    break
            for i in range(self.batch_size):
                w = (i+1)/self.batch_size
                batch_point[i,:] = current_point*w + self.lx[0,:]*(1-w)
                if self.detect_alias(batch_point[i,:].astype(int),self.points):
                    random_move = np.array([random.randint(-1,1) for _ in range(self.dim)])
                    batch_point[i,:] = batch_point[i,:] + random_move
            return batch_point.astype(int)
        else:
            self.expore_n += 1
            current_point = np.array(np.sum(point_lx,axis=0))
            batch_point_idx = 0
            refresh_limit = 10 + self.batch_size
            while(1):
                if refresh_limit == 0:
                    if (self.detect_alias(current_point.astype(int),self.points) or self.detect_alias(current_point.astype(int),batch_point)):
                        current_point = (1-w_best) * self.init_point(1) +  (w_best) * np.sum(point_lx,axis=0)
                    else:
                        batch_point[batch_point_idx,:] = current_point
                        batch_point_idx += 1
                        if batch_point_idx == self.batch_size:
                            break
                else:
                    if (self.detect_alias(current_point.astype(int),self.points) or self.detect_alias(current_point.astype(int),batch_point)):
                        random_move = np.array([random.randint(-1,1) for _ in range(self.dim)])
                        current_point = self.lx[0,:]+random_move
                        refresh_limit -= 1
                    else:
                        batch_point[batch_point_idx,:] = current_point
                        batch_point_idx += 1
                        if batch_point_idx == self.batch_size:
                            break
            return batch_point.astype(int)
    def update_points_observations(self,new_point,new_observation):
        self.points         = np.append(self.points,new_point,axis=0)
        self.observations   = np.append(self.observations,new_observation,axis=0)
        
    def optimization(self) -> np.array:
        '''
        #1# generate initial point
        #2# get initial samples
        #3# sort observations
        #4# a function to calculate l(x) and g(x)
        #5# use SGD to find the next query point
        #6# obtain new observations
        #7# go to #3# if not exit
        #8# return the best observation
        '''
        self.points = self.init_point(self.batch_size)
        self.observations = self.object_func(self.points)
        n_send = np.ceil(self.n_init_points/self.batch_size)-1
        for i in range(int(n_send)):
            #1# generate initial point
            init_points         = self.init_point(self.batch_size)
            #2# get initial samples
            init_observations   = self.object_func(init_points)
            self.update_points_observations(init_points,init_observations)
        # print("init points: ")
        # print(self.points)
        # print("init values: ")
        # print(self.observations)
        #3# sort observations
        self.expore_n = 0
        for i in range(self.n_iterations):
            self.sort_observations()
            #4# a function to calculate l(x) and g(x)

            #5# use SGD to find the next query point
            next_query_point    = self.SGD_explore_exploit()
            #6# obtain new observations
            new_observation     = self.object_func(next_query_point)
                #update points and observations
            self.update_points_observations(next_query_point,new_observation)
            # if i%20 == 0: print(i) 
        print("# of explore: ",self.expore_n)

        #7# go to #3# if not exit
        #8# return the best observation
        self.sort_observations()
        self.points = np.array(self.points)
        self.observations = np.array(self.observations)
        result = {
            "configs": self.points.tolist(),
            "observations": self.observations.tolist(),
            "best_observations": self.best.tolist(),
        }
        
        # with open("./TPE_result.json",'w') as result_file:
        #     json.dump(result, result_file,)
        # return self.lx[0,:]

if __name__ == "__main__":
    def object_func_test(input_points:np.array) -> float:
        R,object_value  = np.zeros((len(input_points),1),dtype=float),np.zeros((len(input_points),1),dtype=float)
        for i in range(len(input_points)):
            R[i] = np.sqrt(sum((input_points[i][:]-15)**2)) + 3.1; 
            object_value[i] = -np.sin(0.06*R[i])/(np.log10(R[i]+1e-8)+0.1)
        return object_value

    def Rosenbrock_WLO(input_points:np.array) -> float:

        object_value  = np.zeros((len(input_points),1),dtype=float)
        for i in range(len(input_points)):
            object_value[i] = np.sum(100*((input_points[i,1:-1]-input_points[i,0:-2])**2))+np.sum((1-input_points[i,:])**2)
        return object_value

    def Sphere_WLO(input_points:np.array) -> float:

        object_value  = np.zeros((len(input_points),1),dtype=float)
        for i in range(len(input_points)):
            object_value[i] = np.sum((input_points[i,:]-0)**2)
        return object_value


    sphere = 2
    dim = 10

    if sphere == 1:
        search_space_test = np.array([[-16,16] for _ in range(dim)])
        opt = optimizer(objec_func=Sphere_WLO,n_iterations=200,n_init_points=15,search_space=search_space_test,SGD_learn_rate=10,batch_size=2)
        test_point = np.ones((1,len(search_space_test)),dtype=int)*0
        print("solution is ", test_point,", obj value is:" + str(Sphere_WLO(test_point)))

    else:
        search_space_test = np.array([[-16,16] for _ in range(dim)])
        # print("best obj value is: -0.73529")
        print("best obj value is: -0.33")
        opt = optimizer(objec_func=Rosenbrock_WLO,n_iterations=200,n_init_points=15,search_space=search_space_test,SGD_learn_rate=10,batch_size=2)

    start_time  = time.time()
    temp=opt.optimization()
    end_time    = time.time()
    


    print("best_config: " + str(temp))
    print("the best object value is: " + str(opt.best))
    print("Time per iteration: " + str((end_time-start_time)/(opt.n_init_points+opt.n_iterations)) + " s/ite")


    plt.figure(1)
    x=np.array(np.linspace(1,len(opt.observations),len(opt.observations)),dtype=int)
    y=opt.observations.flatten()
    plt.plot(x,y,'bo-')
    plt.xlim([0, opt.n_init_points+opt.n_iterations*opt.batch_size])
    plt.show()

    print("============")
    print(opt.lx[0:5])
    print("============")


# for i in range(len(opt.points)+15):
#     plt.figure(1)
#     x=np.array(np.linspace(1,len(opt.observations[0:i]),len(opt.observations[0:i])),dtype=int)
#     y=opt.observations[0:i].flatten()
#     plt.plot(x,y,'bo-')
#     plt.xlim([0, opt.n_init_points+opt.n_iterations])
    
#     plt.draw()

#     # plt.figure(2)
#     # x=opt.points[0:i,0]
#     # y=opt.points[0:i,1]
#     # plt.plot(x,y,'bo')
#     # plt.xlim([8,32])
#     # plt.ylim([8,32])
#     # plt.grid()
#     # plt.draw()

#     plt.pause(1/20)
# plt.show()


