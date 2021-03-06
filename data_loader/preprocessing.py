import numpy as np
from skimage.segmentation import slic
from skimage.transform import resize
import os
import warnings
from matplotlib import image as mpimg
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from data_loader.load_utils import save_obj, load_obj
from numpy import unique
from numpy import random
import parmap
import time
import argparse
# To remove future warning from being printed out
warnings.simplefilter(action='ignore', category=FutureWarning)


def load_image(infilename):
    """ Reads images """
    data = mpimg.imread(infilename)
    return data


def load_batch(path, pimg, pgt, nfiles, batch_size=1000, startAt = 0):
    # sample randomly
    #randomise = np.random.choice(nfiles, size=batch_size, replace=False)
    # generate file lists
    print('Reading file names ..')
    filelist = []
    filelist = [os.listdir(path + pimg)[i] for i in range(startAt, startAt + batch_size)]
    gtlist = ['gt_' + filelist[i] for i in range(len(filelist))]
    print('read')
    # initialise datasets
    imgs = []
    gts = []
    # read files
    print('Reading ', batch_size, ' files...')
    i = 0
    while i < batch_size:
        name = path + pimg + filelist[i]
        gtname = path + pgt + gtlist[i]
        i += 1
        if name.endswith(".jpg"):
            imgs.append(load_image(name))
            gts.append(load_image(gtname))

    imgs = np.asarray(imgs)
    gts = np.asarray(gts)
    print('Read ', i, ' files.')
    print('Check: img size', imgs.shape, '\tgt size', gts.shape)
    return imgs, gts

def load_test_batch(path, pimg, nfiles, batch_size=1000):
    # sample randomly
    randomise = np.random.choice(nfiles, size=batch_size, replace=False)
    # generate file lists
    print('Reading file names ..')
    filelist = [os.listdir(path + pimg)[i] for i in randomise]
    print('read')
    # initialise datasets
    imgs = []
    # read files
    print('Reading ', batch_size, ' files...')
    i = 0
    while i < batch_size:
        name = path + pimg + filelist[i]
        i += 1
        if name.endswith(".jpg"):
            imgs.append(load_image(name))

    imgs = np.asarray(imgs)
    print('Read ', i, ' files.')
    print('Check: img size', imgs.shape)
    return imgs


def box(seg):
    list_box = []
    for i in range(np.max(seg)+1):
        xind = np.nonzero(seg.ravel('C') == i)
        [xmax, _] = np.unravel_index(np.max(xind), seg.shape, order = 'C')
        [xmin, _] = np.unravel_index(np.min(xind), seg.shape, order = 'C')
        yind = np.nonzero(seg.ravel('F') == i)
        [_, ymax] = np.unravel_index(np.max(yind), seg.shape, order = 'F')
        [_, ymin] = np.unravel_index(np.min(yind), seg.shape, order = 'F')
        list_box.append(np.array([xmax, ymax, xmin, ymin]))
    return list_box


def patch_cat(gt_SLIC, thres1, thres2):
    gt = gt_SLIC[0]
    SLIC = gt_SLIC[1]
    label_list = []
    for i in range(np.max(SLIC)+1):
        num = np.sum(gt[SLIC == i] > 125)
        denom = gt[SLIC == i].size
        size_true = np.sum(gt > 125)
        if float(num)/float(denom)>thres1:
            label_list.append(1)
        else:
            if float(size_true) > 0 and float(num)/float(size_true) > thres2:
                label_list.append(1)
            else:
                label_list.append(0)
    return label_list


def xpatchify(img_SLIC_boxed):
    img = img_SLIC_boxed[0]
    SLIC = img_SLIC_boxed[1]
    boxed = img_SLIC_boxed[2]
    list_patches = []
    for i in range(np.max(SLIC)+1):
        [inda, indb] = np.nonzero(SLIC!=i)
        imtemp = np.copy(img)
        imtemp[inda,indb,:] = 0
        x_temp = imtemp[int(boxed[i][2]):int(boxed[i][0]),
                     int(boxed[i][3]):int(boxed[i][1])]
        x_train = resize(x_temp, (40,40))
        list_patches.append(x_train)
    return(list_patches)


def get_labeled_patches(imgs, gts, n_segments=100, thres1=0.2, thres2=0.2):
    """
    Get all the patches from the set of images.
    :param imgs: images
    :param gts: masks
    :param n_segments: max number of patches for image
    :param thres1: label = 1 if a proportion bigger than thres1 in the patch is masked as 1
    :param thres2: label = 1 if pixels masked as 1 in patch / total number of pixels masked as 1 in the picture > thres2
    :return: patches: list of patches, size [len(img), n_patches_per_image, 80,80]
    :return: labels: list of labels per each patch, size [len(img), n_patches_per_image]
    """
    n = len(imgs)
    SLIC_list = np.asarray([slic(imgs[i, :], n_segments, compactness=20, sigma=10) for i in range(len(imgs))])

    # run box function to find all superpixel patches sizes
    boxes = parmap.map(box, SLIC_list)

    # populating x_train
    patches = parmap.map(xpatchify, zip(imgs, SLIC_list, boxes))

    # labels
    labels = parmap.map(patch_cat, zip(gts, SLIC_list), thres1, thres2)

    return patches, labels

def get_patches(imgs, n_segments=100, thres1=0.2, thres2=0.2):
    """
    Get all the patches from the set of images.
    :param imgs: images
    :param gts: masks
    :param n_segments: max number of patches for image
    :param thres1: label = 1 if a proportion bigger than thres1 in the patch is masked as 1
    :param thres2: label = 1 if pixels masked as 1 in patch / total number of pixels masked as 1 in the picture > thres2
    :return: patches: list of patches, size [len(img), n_patches_per_image, 80,80]
    :return: labels: list of labels per each patch, size [len(img), n_patches_per_image]
    """
    n = len(imgs)
    SLIC_list = np.asarray([slic(imgs[i, :], n_segments, compactness=20, sigma=10) for i in range(len(imgs))])

    # run box function to find all superpixel patches sizes
    boxes = parmap.map(box, SLIC_list)

    # populating x_train
    patches = parmap.map(xpatchify, zip(imgs, SLIC_list, boxes))

    return patches, SLIC_list


def balanced_sample_maker(X, y, random_seed=None):
    """ return a balanced data set by oversampling minority class and downsampling majority class
        current version is developed on assumption that the positive
        class is the minority.

    Parameters:
    ===========
    X: {numpy.ndarrray}
    y: {numpy.ndarray}
    """
    uniq_levels = unique(y)
    if len(uniq_levels) < 2:
        print("Not enough data, there are no images with a boat!")
        exit(0)
    uniq_counts = {level: sum(y == level) for level in uniq_levels}

    if not random_seed is None:
        random.seed(random_seed)

    # find observation index of each class levels
    groupby_levels = {}
    for ii, level in enumerate(uniq_levels):
        obs_idx = [idx for idx, val in enumerate(y) if val == level]
        groupby_levels[level] = obs_idx

    # downsampling on observations of negative label
    sample_size = uniq_counts[0]  # number of negative samples
    down_sample_idx = random.choice(groupby_levels[0], size=int(sample_size / 10), replace=True).tolist()

    # oversampling on observations of positive label
    over_sample_idx = random.choice(groupby_levels[1], size=int(sample_size / 10), replace=True).tolist()
    balanced_copy_idx = down_sample_idx + over_sample_idx
    random.shuffle(balanced_copy_idx)

    return X[balanced_copy_idx, :], y[balanced_copy_idx]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--startAt",
                        help="image index to start preprocess", type=int)
    args = parser.parse_args()
    index = args.startAt if args.startAt else 0
    path = './data/'
    pimg = 'train_sample/'
    pgt = 'train_maps/'
    nfiles = len(os.listdir(path + pimg))
    startTime = time.time()
    imgs, gts = load_batch(path, pimg, pgt, nfiles, batch_size=1000, startAt = index)
    list_patches, list_labels = get_labeled_patches(imgs, gts)
    print("Got the patches and labels.")

    # flatten the data
    labels_flat = []
    [labels_flat.append(l) for patches_labels in list_labels for l in patches_labels]
    labels_flat = np.array(labels_flat)

    patches_flat = []
    [patches_flat.append(patch) for patches_img in list_patches for patch in patches_img]
    patches_flat = np.array(patches_flat)

    print("\nNumber of patches: {}".format(len(patches_flat)))
    print("Number of labels: {} \n".format(len(labels_flat)))

    # balance the data
    X, y = balanced_sample_maker(patches_flat, labels_flat)

    print("Length of patches after balancing: {} ".format(len(X)))
    print("Length of saved labels after balancing: {} \n".format(len(y)))

    # save the data
    save_obj(X, 'data/patches_' + str(index))
    save_obj(y, 'data/labels_patches_' + str(index))
    print("Created patches and labels\n")
    print("Time is {}".format(time.time() - startTime))
    X = load_obj('data/patches_' + str(index))
    y = load_obj('data/labels_patches_' + str(index))

    print("Length of saved patches: {} \n".format(len(X)))
    print("Length of saved labels: {} \n".format(len(y)))
