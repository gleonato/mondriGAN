# MondriGAN: Criar uma Imagem baseada no acervo de Piet Mondrian

import keras
# from keras.datasets import mnist
from keras.layers import Input, Dense, Reshape, Flatten
from keras.layers import BatchNormalization
from keras.layers.advanced_activations import LeakyReLU
from keras.models import Sequential, Model
from keras.optimizers import Adam
import matplotlib.pyplot as plt
import numpy as np
import ssl
import cv2
import os

# from keras.engine.topology import Container      # Gambi

from keras.engine.network import Network      # Gambi


# Parametros do model

DATADIR = "/Users/gustavoleonato/Projects/DeepFakeProject/DFCreation/mondriGAN/Piet_Mondrian"
IMG_SIZE = 172 # 56
EPOCHS = 400001
BATCH_SIZE = 132


ssl._create_default_https_context = ssl._create_unverified_context

class GAN():
    def __init__(self):
        self.img_rows = IMG_SIZE
        self.img_cols = IMG_SIZE
        self.channels = 1
        self.img_shape = (self.img_rows,self.img_cols, self.channels)
        self.latent_dim = 100
        optimizer = Adam(0.0002, 0.5)

        print('Discriminator modeling:')
        
        model = Sequential()

        model.add(Flatten(input_shape=self.img_shape))
        model.add(Dense(512))
        model.add(LeakyReLU(alpha=0.2))
        model.add(Dense(256))
        model.add(LeakyReLU(alpha=0.2))
        model.add(Dense(1, activation='sigmoid'))
        model.summary()
        img = Input(shape=self.img_shape)
        validity = model(img)

        # Build and Compile the Discriminator Model

        self.discriminator = Model(img, validity)
        self.discriminator.compile(loss='binary_crossentropy',
                                   optimizer=optimizer,
                                   metrics=['accuracy'])
        self.discriminator_fixed = Network(img, validity)    # -> I Add THIS CONTAINER!
        
        # Build & Compile the Generator Model 
        self.generator = self.build_generator()
        
        #Creates the NOISE (z) to be input for generator and produce the image
        z = Input(shape=(self.latent_dim,))

        # Produce the image 
        img = self.generator(z)

        # This steps ensure when we train our Netowrks we ONLY train the Generator Net 
        # self.discriminator.trainable = False
        self.discriminator_fixed.trainable = False

        # specifies that our Discriminator will take the images  generated by our Generator + true dataset and set its output 
        # to a parameter called validity, which will indicate whether the input is real or not.
        # validity = self.discriminator(img)
        validity = self.discriminator_fixed(img)

        # combined the models and also set our loss function and optimizer. The ultimate goal here is for the Generator to fool the Discriminator.
        self.combined = Model(z, validity)
        # self.combined = Model(z, self.discriminator_fixed(validity))   # Use container
        self.combined.compile(loss='binary_crossentropy', optimizer=optimizer)

    def build_generator(self):

        print('Generator modeling:')

        model = Sequential()

        model.add(Dense(256, input_dim=self.latent_dim))
        model.add(LeakyReLU(alpha=0.2))
        model.add(BatchNormalization(momentum=0.8))
        model.add(Dense(512))
        model.add(LeakyReLU(alpha=0.2))
        model.add(BatchNormalization(momentum=0.8))
        model.add(Dense(1024))
        model.add(LeakyReLU(alpha=0.2))
        model.add(BatchNormalization(momentum=0.8))
        model.add(Dense(np.prod(self.img_shape), activation='tanh'))
        model.add(Reshape(self.img_shape))
        model.summary()
        noise = Input(shape=(self.latent_dim,))
        img = model(noise)
        return Model(noise, img)


    def train(self, epochs, batch_size=128, sample_interval=50):
        print('Start training...')
        training_data = []

        for img in os.listdir(DATADIR):
            try:
                # img_array = cv2.imread(os.path.join(DATADIR,img), cv2.IMREAD_GRAYSCALE)
                img_array = cv2.imread(os.path.join(DATADIR,img), cv2.IMREAD_UNCHANGED)
                print(img,img_array.shape)
                # cv2.imshow('image',img_array)
                # cv2.waitKey(0)
                new_array = cv2.resize(img_array,(IMG_SIZE,IMG_SIZE))
                print(new_array.shape)
                # cv2.imshow('resized image',new_array)
                # cv2.waitKey(0)
                training_data.append([new_array])
                print(training_data.shape)
            except Exception as e:
                # print("Exception!")
                pass
        
        # PRint array lenght
        print(len(training_data))

        # Load data into array
        X_train = [] 
        for images in training_data:
            X_train.append(images)
        
        # Convert list to numpy array and reshape it to expected input format i.e. (58,58,1)
        X_train = np.array(X_train).reshape(-1,IMG_SIZE,IMG_SIZE)
        print('NP array shape:')
        print(X_train.shape)
        print('Sample:')
        print(X_train[0])
        X_train = X_train / 127.5 - 1.
        X_train = np.expand_dims(X_train, axis=3)
        valid = np.ones((batch_size, 1))
        fake = np.zeros((batch_size, 1))

        for epoch in range(epochs):
            print('epoch: ', epoch)
            idx = np.random.randint(0, X_train.shape[0], batch_size)

            imgs = X_train[idx]
            noise = np.random.normal(0, 1, (batch_size, self.latent_dim))

            g_loss = self.combined.train_on_batch(noise, valid)
            gen_imgs = self.generator.predict(noise)
            d_loss_real = self.discriminator.train_on_batch(imgs, valid)
            d_loss_fake = self.discriminator.train_on_batch(gen_imgs, fake)
            d_loss = 0.5 * np.add(d_loss_real, d_loss_fake)

            print("%d [D loss: %f, acc.: %.2f%%] [G loss: %f]" % (epoch, d_loss[0], 100 * d_loss[1], g_loss))
            # print("%d [D loss: %f, acc.: %.2f%%]" % (epoch, d_loss[0], 100 * d_loss[1]))

            if epoch % sample_interval == 0:
                print('printing sample...')
                self.sample_image(epoch)
                self.sample_images(epoch)

    def sample_images(self, epoch):
        r, c = 5, 5
        noise = np.random.normal(0, 1, (r * c, self.latent_dim))
        gen_imgs = self.generator.predict(noise)
        # print(gen_imgs.shape)
        gen_imgs = 0.5 * gen_imgs + 0.5
        fig, axs = plt.subplots(r, c)
        cnt = 0
        for i in range(r):
            for j in range(c):
                # axs[i, j].imshow(gen_imgs[cnt, :, :, 0], cmap='gray')
                axs[i, j].imshow(gen_imgs[cnt, :, :, 0])
                axs[i, j].axis('off')
                cnt += 1
        fig.savefig("images/%d.png" % epoch)
        plt.close()
    
    def sample_image(self, epoch):
        # r, c = 5, 5
        noise = np.random.normal(0, 1, (1, self.latent_dim))
        gen_img = self.generator.predict(noise)
        gen_img = 0.5 * gen_img + 0.5
        plt.imshow(gen_img[0, :, :, 0]).figure.savefig("images/1-image-%d.png" % epoch)
        plt.close()


if __name__ == '__main__':
    gan = GAN()
    gan.train(epochs=EPOCHS, batch_size=BATCH_SIZE, sample_interval=100)
