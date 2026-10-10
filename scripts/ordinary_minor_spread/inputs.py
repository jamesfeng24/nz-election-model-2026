"""Pin the Stage83 consumed inputs (design, Stage67 flags, Stage44/45 records and scales, harness code)."""
from .common import PREFIX, pin, read, save, arguments


def main():
    args = arguments()
    value = pin()
    if args.check:
        if read(PREFIX + '/input-contract.json') != value:
            raise ValueError('Stale Stage83 input contract')
    else:
        save('input-contract.json', value)
    print('Stage83 input contract ' + ('verified' if args.check else 'written'))


if __name__ == '__main__':
    main()
