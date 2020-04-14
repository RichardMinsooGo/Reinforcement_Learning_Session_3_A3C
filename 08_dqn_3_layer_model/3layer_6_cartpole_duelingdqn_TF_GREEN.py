import tensorflow as tf
import gym
import numpy as np
import random as ran
from collections import deque
env = gym.make('CartPole-v0')
INPUT_SIZE = env.observation_space.shape[0]
OUTPUT_SIZE = env.action_space.n

Alpha = 0.001
Gamma = 0.99
N_EPISODES = 5000
N_train_result_replay = 20
H_SIZE_01 = 512
H_SIZE_02 = 511
H_SIZE_03 = 510
TARGET_UPDATE_CYCLE = 10

H_SIZE_15_state = 256
H_SIZE_15_action = 256
H_SIZE_16_state = OUTPUT_SIZE
H_SIZE_16_action = OUTPUT_SIZE

replay_buffer = []
SIZE_R_M = 50000
MINIBATCH = 64

MIN_E = 0.0
EPSILON_DECAYING_EPISODE = N_EPISODES * 0.01

def annealing_epsilon(episode: int, min_e: float, max_e: float, target_episode: int) -> float:

    slope = (min_e - max_e) / (target_episode)
    intercept = max_e

    return max(min_e, slope * episode + intercept)

X=tf.placeholder(dtype=tf.float32, shape=(None, INPUT_SIZE), name="input_X")
Y=tf.placeholder(dtype=tf.float32, shape=(None, OUTPUT_SIZE), name="output_Y")

W01_m = tf.get_variable('W01_m',shape=[INPUT_SIZE, H_SIZE_01]
                        ,initializer=tf.contrib.layers.xavier_initializer())
W02_m = tf.get_variable('W02_m',shape=[H_SIZE_01, H_SIZE_02]
                        ,initializer=tf.contrib.layers.xavier_initializer())
W03_m = tf.get_variable('W03_m',shape=[H_SIZE_02, H_SIZE_03]
                        ,initializer=tf.contrib.layers.xavier_initializer())
W15_m_state  = tf.get_variable('W15_m_state',shape=[H_SIZE_03, H_SIZE_15_state]
                              ,initializer=tf.contrib.layers.xavier_initializer())
W15_m_action = tf.get_variable('W15_m_action',shape=[H_SIZE_03, H_SIZE_15_action]
                               ,initializer=tf.contrib.layers.xavier_initializer())
W16_m_state  = tf.get_variable('W16_m_state',shape=[H_SIZE_15_state, H_SIZE_16_state]
                              ,initializer=tf.contrib.layers.xavier_initializer())
W16_m_action = tf.get_variable('W16_m_action',shape=[H_SIZE_15_action, H_SIZE_16_action]
                               ,initializer=tf.contrib.layers.xavier_initializer())

B01_m = tf.Variable(tf.zeros([1],dtype=tf.float32))
B02_m = tf.Variable(tf.zeros([1],dtype=tf.float32))
B03_m = tf.Variable(tf.zeros([1],dtype=tf.float32))
B15_m_state       = tf.Variable(tf.zeros([1],dtype=tf.float32))
B15_m_action      = tf.Variable(tf.zeros([1],dtype=tf.float32))
B16_m_state       = tf.Variable(tf.zeros([1],dtype=tf.float32))
B16_m_action      = tf.Variable(tf.zeros([1],dtype=tf.float32))

_LAY01_m = tf.nn.relu(tf.matmul(X,W01_m)+B01_m)
_LAY02_m = tf.nn.relu(tf.matmul(_LAY01_m,W02_m)+B02_m)
_LAY03_m = tf.nn.relu(tf.matmul(_LAY02_m,W03_m)+B03_m)

_LAY15_m_state    = tf.nn.relu(tf.matmul(_LAY03_m,W15_m_state)+B15_m_state)
_LAY15_m_action   = tf.nn.relu(tf.matmul(_LAY03_m,W15_m_action)+B15_m_action)

_LAY16_m_state    = tf.matmul(_LAY15_m_state,W16_m_state) + B16_m_state
_LAY16_m_action   = tf.matmul(_LAY15_m_action,W16_m_action) + B16_m_action

LAY16_m_advantage = tf.subtract(_LAY16_m_action, tf.reduce_mean(_LAY16_m_action))

Qpred_m = tf.add(_LAY16_m_state, LAY16_m_advantage)

W01_t = tf.get_variable('W01_t',shape=[INPUT_SIZE, H_SIZE_01])
W02_t = tf.get_variable('W02_t',shape=[H_SIZE_01, H_SIZE_02])
W03_t = tf.get_variable('W03_t',shape=[H_SIZE_02, H_SIZE_03])
W15_t_state  = tf.get_variable('W15_t_state',shape=[H_SIZE_03, H_SIZE_15_state])
W15_t_action = tf.get_variable('W15_t_action',shape=[H_SIZE_03, H_SIZE_15_action])
W16_t_state  = tf.get_variable('W16_t_state',shape=[H_SIZE_15_state, H_SIZE_16_state])
W16_t_action = tf.get_variable('W16_t_action',shape=[H_SIZE_15_action, H_SIZE_16_action])

B01_t = tf.Variable(tf.zeros([1],dtype=tf.float32))
B02_t = tf.Variable(tf.zeros([1],dtype=tf.float32))
B03_t = tf.Variable(tf.zeros([1],dtype=tf.float32))
B15_t_state  = tf.Variable(tf.zeros([1],dtype=tf.float32))
B15_t_action = tf.Variable(tf.zeros([1],dtype=tf.float32))
B16_t_state  = tf.Variable(tf.zeros([1],dtype=tf.float32))
B16_t_action = tf.Variable(tf.zeros([1],dtype=tf.float32))

LAY01_t = tf.nn.relu(tf.matmul(X ,W01_t)+B01_t)
LAY02_t = tf.nn.relu(tf.matmul(LAY01_t ,W02_t)+B02_t)
LAY03_t = tf.nn.relu(tf.matmul(LAY02_t ,W03_t)+B03_t)

LAY15_t_state     = tf.nn.relu(tf.matmul(LAY03_t,W15_t_state)+B15_t_state)
LAY15_t_action    = tf.nn.relu(tf.matmul(LAY03_t,W15_t_action)+B15_t_action)

LAY16_t_state     = tf.matmul(LAY15_t_state,W16_t_state) + B16_t_state
LAY16_t_action    = tf.matmul(LAY15_t_action,W16_t_action) + B16_t_action

LAY16_t_advantage = tf.subtract(LAY16_t_action, tf.reduce_mean(LAY16_t_action))

Qpred_t = tf.add(LAY16_t_state, LAY16_t_advantage)

rlist=[0]
last_N_game_reward=[0]

episode = 0

LossValue = tf.reduce_sum(tf.square(Y-Qpred_m))
optimizer = tf.train.AdamOptimizer(Alpha, epsilon=0.01)
train = optimizer.minimize(LossValue)

model_path = "/tmp/RL/save/06_DuelingDQN/model.ckpt"
saver = tf.train.Saver()

init = tf.global_variables_initializer()

with tf.Session() as sess:
    sess.run(init)
    sess.run(W01_t.assign(W01_m))
    sess.run(W02_t.assign(W02_m))
    sess.run(W03_t.assign(W03_m))
    sess.run(W15_t_state.assign(W15_m_state))
    sess.run(W15_t_action.assign(W15_m_action))
    sess.run(W16_t_state.assign(W16_m_state))
    sess.run(W16_t_action.assign(W16_m_action))
    
    sess.run(B01_t.assign(B01_m))
    sess.run(B02_t.assign(B02_m))
    sess.run(B03_t.assign(B03_m))
    sess.run(B15_t_state.assign(B15_m_state))
    sess.run(B15_t_action.assign(B15_m_action))
    sess.run(B16_t_state.assign(B16_m_state))
    sess.run(B16_t_action.assign(B16_m_action))
        
    last_N_game_reward = deque(maxlen=100)
    last_N_game_reward.append(0)
    replay_buffer = deque(maxlen=SIZE_R_M)
    
    for episode in range(N_EPISODES):        
        state = env.reset()
        e = annealing_epsilon(episode, MIN_E, 1.0, EPSILON_DECAYING_EPISODE)
        rall = 0
        done = False
        count = 0
        while not done and count < 10000 :
            #env.render()
            count += 1
            state_reshape = np.reshape(state,[1,INPUT_SIZE])
            Q_m = sess.run(Qpred_m, feed_dict={X:state_reshape})
            
            if e > np.random.rand(1):
                action = env.action_space.sample()
            else:
                action = np.argmax(Q_m)
                
            nextstate, reward, done, _ = env.step(action)
            replay_buffer.append([state_reshape,action,reward,nextstate,done,count])            
            rall += reward
            state = nextstate

        if episode % TARGET_UPDATE_CYCLE == 0 and len(replay_buffer) > MINIBATCH:

            for sample in ran.sample(replay_buffer, MINIBATCH):

                state_R_M, action_R_M, reward_R_M, nextstate_R_M, done_R_M ,count_R_M = sample
                Q_Global = sess.run(Qpred_m, feed_dict={X: state_R_M})
                
                if done_R_M:
                    if count_R_M < env.spec.timestep_limit :
                        Q_Global[0, action_R_M] = -100
                else:
                    nextstate_reshape_R_M = np.reshape(nextstate_R_M,[1,INPUT_SIZE])
                    Q_target = sess.run(Qpred_t, feed_dict={X: nextstate_reshape_R_M})
                    Q_Global[0, action_R_M] = reward_R_M + Gamma * np.max(Q_target)
                
                _, loss = sess.run([train, LossValue], feed_dict={X: state_R_M, Y: Q_Global})

            sess.run(W01_t.assign(W01_m))
            sess.run(W02_t.assign(W02_m))
            sess.run(W03_t.assign(W03_m))
            sess.run(W15_t_state.assign(W15_m_state))
            sess.run(W15_t_action.assign(W15_m_action))
            sess.run(W16_t_state.assign(W16_m_state))
            sess.run(W16_t_action.assign(W16_m_action))
            sess.run(B01_t.assign(B01_m))
            sess.run(B02_t.assign(B02_m))
            sess.run(B03_t.assign(B03_m))
            sess.run(B15_t_state.assign(B15_m_state))
            sess.run(B15_t_action.assign(B15_m_action))
            sess.run(B16_t_state.assign(B16_m_state))
            sess.run(B16_t_action.assign(B16_m_action))            
            
            print("Episode {:>5} reward:{:>5} average reward:{:>5.2f} recent N Game reward:{:>5.2f} Loss:{:>5.2f} memory length:{:>5}"
                  .format(episode, rall, np.mean(rlist), np.mean(last_N_game_reward),loss,len(replay_buffer)))
           
        last_N_game_reward.append(rall)
        rlist.append(rall)
        
        if len(last_N_game_reward) == last_N_game_reward.maxlen:
            avg_reward = np.mean(last_N_game_reward)
            if avg_reward > 199.0:
                print("Game Cleared within {:>5} episodes with avg reward {:>5.2f}".format(episode, avg_reward))
                break

    save_path = saver.save(sess, model_path)
    print("Model saved in file: ",save_path)

with tf.Session() as sess:
    sess.run(tf.global_variables_initializer())
    saver.restore(sess, model_path)
    print("Play Cartpole!")
    
    rlist=[]
    
    for episode in range(N_train_result_replay):        
        state = env.reset()
        rall = 0
        done = False
        count = 0
        
        while not done :
            env.render()
            count += 1
            state_reshape = np.reshape(state, [1, INPUT_SIZE])
            Q_Global = sess.run(Qpred_m, feed_dict={X: state_reshape})
            action = np.argmax(Q_Global)
            state, reward, done, _ = env.step(action)
            rall += reward

        rlist.append(rall)
        print("Episode : {:>5} rewards ={:>5}. averge reward : {:>5.2f}".format(episode, rall,
                                                                        np.mean(rlist)))