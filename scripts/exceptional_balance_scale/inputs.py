"""Pin the Stage67 consumed inputs (design, flags, Stage60 fit and harness code, Stage48 inputs)."""
from .common import PREFIX, pin, read, save, arguments


def main():
    args = arguments()
    value = pin()
    if args.check:
        if read(PREFIX + '/input-contract.json') != value:
            raise ValueError('Stale Stage67 input contract')
    else:
        save('input-contract.json', value)
    print('Stage67 input contract ' + ('verified' if args.check else 'written'))


if __name__ == '__main__':
    main()
