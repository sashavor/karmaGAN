"""
build_history: gx_history, fy_history

build_reader: x_images, y_images

"""
import glob
import numpy as np
import os
import scipy.misc
import tensorflow as tf

from six.moves import range

from model import build_cycle_gan


FLAGS = tf.app.flags.FLAGS

tf.app.flags.DEFINE_float(
    'learning_rate', 0.0002, '')

tf.app.flags.DEFINE_string(
    'mode', 'gx', 'gx / fy')
tf.app.flags.DEFINE_string(
    'logs_dir_path', None, 'path to the directory for logs')
tf.app.flags.DEFINE_string(
    'ckpt_dir_path', None, 'path to the directory for checkpoint')
tf.app.flags.DEFINE_string(
    'x_images_dir_path', None, 'path to the dir for image x')
tf.app.flags.DEFINE_string(
    'y_images_dir_path', None, 'path to the dir for image y')
tf.app.flags.DEFINE_string(
    'source_image_path', None, 'path to source test image')
tf.app.flags.DEFINE_string(
    'result_image_path', None, 'path to result test image')
tf.app.flags.DEFINE_string(
    'source_images_dir_path', None, 'path to source test image')
tf.app.flags.DEFINE_string(
    'result_images_dir_path', None, 'path to result test image')

tf.app.flags.DEFINE_boolean(
    'is_training', True, 'build and train the model')

tf.app.flags.DEFINE_integer(
    'batch_size', 1, 'batch size for training')
tf.app.flags.DEFINE_integer(
    'history_size', 50, 'history size for training discriminator')
tf.app.flags.DEFINE_integer(
    'checkpoint_step', 10000, '')
tf.app.flags.DEFINE_integer(
    'summary_train_image_step', 100, '')
tf.app.flags.DEFINE_integer(
    'summary_valid_image_step', 10000, '')
tf.app.flags.DEFINE_integer(
    'learning_rate_decay_head_at_step', 10, '')
tf.app.flags.DEFINE_integer(
    'learning_rate_decay_tail_at_step', 20, '')


def update_image_pool(image_pool, xs_fake, ys_fake):
    """
    """
    if 'xs_fake' not in image_pool or 'ys_fake' not in image_pool:
        # there is nothing in the pool.
        image_pool['xs_fake'] = xs_fake
        image_pool['ys_fake'] = ys_fake
    elif image_pool['xs_fake'].shape[0] < FLAGS.history_size:
        # the pool is not full yet.
        image_pool['xs_fake'] = \
            np.concatenate([image_pool['xs_fake'], xs_fake], axis=0)
        image_pool['ys_fake'] = \
            np.concatenate([image_pool['ys_fake'], ys_fake], axis=0)
    else:
        # the pool is full, pick random samples to replace
        xis = np.random.choice(
            image_pool['xs_fake'].shape[0], [xs_fake.shape[0]], replace=False)
        yis = np.random.choice(
            image_pool['ys_fake'].shape[0], [ys_fake.shape[0]], replace=False)

        image_pool['xs_fake'][xis] = xs_fake
        image_pool['ys_fake'][yis] = ys_fake

    # pick batch samples to train discriminators
    xis = np.random.choice(
        image_pool['xs_fake'].shape[0], [FLAGS.batch_size], replace=False)
    yis = np.random.choice(
        image_pool['ys_fake'].shape[0], [FLAGS.batch_size], replace=False)

    xs_fake = image_pool['xs_fake'][xis, :, :, :]
    ys_fake = image_pool['ys_fake'][yis, :, :, :]

    return xs_fake, ys_fake


def build_batch_reader(paths_image, batch_size):
    """
    """
    file_name_queue = tf.train.string_input_producer(paths_image)

    reader_key, reader_val = tf.WholeFileReader().read(file_name_queue)

    # decode a raw input image
    image = tf.image.decode_jpeg(reader_val, channels=3)

    # to float32 and -1.0 ~ +1.0
    image = tf.cast(image, dtype=tf.float32) / 127.5 - 1.0

    # scale up to increase training data
    image = tf.image.resize_images(image, [264, 264])

    # crop to 256 x 256 for the model.
    # also, a batch need concreate image size
    image = tf.random_crop(image, size=[256, 256, 3])

    # random horizontal flipping to increase training data
    image = tf.image.random_flip_left_right(image)

    # create bacth
    return tf.train.batch(tensors=[image], batch_size=batch_size)


def build_image_batch_reader(dir_path, batch_size):
    """
    """
    paths_wcard = os.path.join(dir_path, '*.jpg')

    paths_image = tf.gfile.Glob(paths_wcard)

    return build_batch_reader(paths_image, batch_size)


def build_summaries(model):
    """
    """
    images_summary = []

    generations = [
        ('summary_x_gx', 'xx_real', 'gx_fake'),
        ('summary_y_fy', 'yy_real', 'fy_fake')]

    for g in generations:
        images = tf.concat([model[g[1]], model[g[2]]], axis=2)

        images = tf.reshape(images, [1, FLAGS.batch_size * 256, 512, 3])

        images = tf.saturate_cast(images * 127.5 + 127.5, tf.uint8)

        summary = tf.summary.image(g[0], images, max_outputs=4)

        images_summary.append(summary)

    #
    summary_loss_d = tf.summary.scalar('d', model['loss_d'])
    summary_loss_dx = tf.summary.scalar('dx', model['loss_dx'])
    summary_loss_dy = tf.summary.scalar('dy', model['loss_dy'])
    summary_d = \
        tf.summary.merge([summary_loss_d, summary_loss_dx, summary_loss_dy])

    summary_loss_g = tf.summary.scalar('g', model['loss_g'])
    summary_loss_gx = tf.summary.scalar('gx', model['loss_gx'])
    summary_loss_fy = tf.summary.scalar('fy', model['loss_fy'])
    summary_g = \
        tf.summary.merge([summary_loss_g, summary_loss_gx, summary_loss_fy])

    return {
        'images': tf.summary.merge(images_summary),
        'loss_d': summary_d,
        'loss_g': summary_g,
    }


def train_one_step(model, summaries, image_pool, reporter):
    """
    """
    lrd_head = FLAGS.learning_rate_decay_head_at_step
    lrd_tail = FLAGS.learning_rate_decay_tail_at_step

    session = tf.get_default_session()

    step = session.run(model['step'])

    if step % FLAGS.checkpoint_step == 0 or step == lrd_tail:
        ckpt_path = os.path.join(FLAGS.ckpt_dir_path, 'model.ckpt')

        tf.train.Saver().save(session, ckpt_path, global_step=model['step'])

    if step == lrd_tail:
        return False

    learning_rate = float(lrd_tail - step) / float(lrd_tail - lrd_head)
    learning_rate = min(1.0, learning_rate) * FLAGS.learning_rate

    #
    fetch = {
        'g_trainer': model['g_trainer'],
        'gx_fake': model['gx_fake'],
        'fy_fake': model['fy_fake'],
        'summary_loss': summaries['loss_g'],
    }

    feeds = {
        model['learning_rate']: learning_rate,
    }

    if step % FLAGS.summary_train_image_step == 0:
        fetch['summary_images'] = summaries['images']

    fetched = session.run(fetch, feed_dict=feeds)

    if 'summary_images' in fetched:
        reporter.add_summary(fetched['summary_images'], step)

    reporter.add_summary(fetched['summary_loss'], step)

    fy_pool, gx_pool = \
        update_image_pool(image_pool, fetched['fy_fake'], fetched['gx_fake'])

    #
    fetch = {
        'd_trainer': model['d_trainer'],
        'summary_loss': summaries['loss_d'],
    }

    feeds = {
        model['learning_rate']: learning_rate,
        model['gx_pool']: gx_pool,
        model['fy_pool']: fy_pool,
    }

    fetched = session.run(fetch, feed_dict=feeds)

    reporter.add_summary(fetched['summary_loss'], step)

    return True


def train():
    """
    """
    ckpt_source_path = tf.train.latest_checkpoint(FLAGS.ckpt_dir_path)

    xx_real = build_image_batch_reader(
        FLAGS.x_images_dir_path, FLAGS.batch_size)

    yy_real = build_image_batch_reader(
        FLAGS.y_images_dir_path, FLAGS.batch_size)

    image_pool = {}

    model = build_cycle_gan(xx_real, yy_real, '')

    summaries = build_summaries(model)

    reporter = tf.summary.FileWriter(FLAGS.logs_dir_path)

    with tf.Session() as session:
        session.run(tf.global_variables_initializer())
        session.run(tf.local_variables_initializer())

        if ckpt_source_path is not None:
            tf.train.Saver().restore(session, ckpt_source_path)

        # give up overlapped old data
        step = session.run(model['step'])

        reporter.add_session_log(
            tf.SessionLog(status=tf.SessionLog.START),
            global_step=step)

        # make dataset reader work
        coord = tf.train.Coordinator()
        threads = tf.train.start_queue_runners(coord=coord)

        while train_one_step(model, summaries, image_pool, reporter):
            pass

        coord.request_stop()
        coord.join(threads)


def prepare_paths():
    """
    """
    image_path_pairs = []

    if FLAGS.source_image_path is not None:
        image_path_pairs.append(
            [FLAGS.source_image_path, FLAGS.result_image_path])

    if FLAGS.source_images_dir_path is not None:
        jpg_names = glob.glob(
            os.path.join(FLAGS.source_images_dir_path, '*.jpg'))
        png_names = glob.glob(
            os.path.join(FLAGS.source_images_dir_path, '*.png'))

        jpg_names = [os.path.basename(name) for name in jpg_names]
        png_names = [os.path.basename(name) for name in png_names]

        src_names = jpg_names + png_names

        for src_name in src_names:
            tar_name = 'test_{}.png'.format(src_name[:-4])

            image_path_pairs.append([
                os.path.join(FLAGS.source_images_dir_path, src_name),
                os.path.join(FLAGS.result_images_dir_path, tar_name)])

    return image_path_pairs


def translate():
    """
    """
    image_path_pairs = prepare_paths()

    reals = tf.placeholder(shape=[None, 256, 256, 3], dtype=tf.uint8)

    flow = tf.cast(reals, dtype=tf.float32) / 127.5 - 1.0

    model = build_cycle_gan(flow, flow, FLAGS.mode)

    fakes = tf.saturate_cast(model['fake'] * 127.5 + 127.5, tf.uint8)

    # path to checkpoint
    ckpt_source_path = tf.train.latest_checkpoint(FLAGS.ckpt_dir_path)

    with tf.Session() as session:
        session.run(tf.global_variables_initializer())
        session.run(tf.local_variables_initializer())

        tf.train.Saver().restore(session, ckpt_source_path)

        for i in range(0, len(image_path_pairs), FLAGS.batch_size):
            path_pairs = image_path_pairs[i:i+FLAGS.batch_size]

            real_images = [scipy.misc.imread(p[0]) for p in path_pairs]

            fake_images = session.run(fakes, feed_dict={reals: real_images})

            for idx, path in enumerate(path_pairs):
                image = np.concatenate(
                    [real_images[idx], fake_images[idx]], axis=1)

                scipy.misc.imsave(path[1], image)


def main(_):
    """
    """
    train() if FLAGS.is_training else translate()


if __name__ == '__main__':
    tf.app.run()
