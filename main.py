from utils import *
from conf import Conf
from process import *

if __name__ == "__main__":
    os.chdir(Path(__file__).parent.resolve())
    conf = Conf()
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', type=str, help='Input file path')
    parser.add_argument('-t', '--test', action='store_true', help='Test env')
    args = parser.parse_args()
    input_file = args.input
    if args.input:
        process = Process()
        process.summary(input_file, True)
    elif args.test:
        main(conf, True)
    else:
        main(conf, False)