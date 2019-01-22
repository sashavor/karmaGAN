					# KarmaGAN: Applying CycleGANs for Generating Images of Climate Change #
							## by Sasha Luccioni ##

For this proof of concept, I compared two GitHub repositories, both implementing CycleGANs in TensorFlow.

CycleGAN1 source: https://github.com/imironhead/ml_gans/tree/master/cyclegan###
#Hyperparameters:
batch-size=4 
history-size=50 
learning-rate=0.0002 
learning-rate-decay-head-at-step=133400 
learning-rate-decay-tail-at-step=266800

Training took 2 days 3 hours to train on Google Cloud Machine Learning Engine (BASIC_GPU)

Code in /CycleGAN1/cyclegan/
Results in /CycleGAN1/test_results/

###CycleGAN2 source: https://github.com/AlessioTonioni/CycleGAN-tensorflow ###

#Hyperparameters:
batch_size=4
epoch=10
number of gen filters in first conv layer= 32
number of discriminator filters in first conv layer= 64
number of input image channels=3
number of output image channels=3
number of iter at starting learning rate = 200
initial learning rate = 0.0002
momentum term of adam = 0.5
weight on L1 term in objective= 10.0
max size of image pool = 50

Training took 15 hrs 45 min on Google Cloud Machine Learning Engine (BASIC_GPU)

Code in /CycleGAN2/cyclegan2/
Results in /CycleGAN2/test_results2/

### Data:
168 images for training:
84 train A (before climate change)
84 train B (after climate change)
18 images for testing (of Montreal)

###Image sources:
- https://www.dailymail.co.uk/news/article-3093474/Risen-ashes-Katrina-Photos-New-Orleans-ten-years-disastrous-hurricane-struck-city-rebuilt.html
- https://frenchmoments.eu/paris-before-and-after-the-2016-floods/
- https://www.thelocal.fr/20180129/before-and-after-the-river-seine-floods-in-paris
- https://www.euronews.com/2018/10/16/before-and-after-pictures-show-the-shocking-impact-of-france-s-floods
- https://www.news18.com/photogallery/india/kerala-floods-before-and-after-pictures-you-must-see-1906953-2.html
- https://pixabay.com/en/photos/montreal/

#######Note#######
There is much to be improved with regards to the diversity and choice of the input images and the quality of the output images. 
This is merely a proof of concept.

