import { afterEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/react';
import { ShareAxis } from './electorates/RangeBar';

const labels = (container: HTMLElement) => [...container.querySelectorAll('.shareaxis span')].map((s) => s.textContent);
const widthOf = (width: number) =>
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({ width } as DOMRect);

describe('share axis labels', () => {
  afterEach(() => vi.restoreAllMocks());

  it('labels every 10% on a wide screen', () => {
    widthOf(600);
    const { container } = render(<ShareAxis axisMax={0.7} />);
    expect(labels(container)).toEqual(['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%']);
  });
  it('thins the labels out when the axis is narrow, so they do not overlap', () => {
    widthOf(200);
    const { container } = render(<ShareAxis axisMax={0.7} />);
    expect(labels(container)).toEqual(['0%', '20%', '40%', '60%']);
  });
  it('never labels beyond the end of the axis', () => {
    widthOf(600);
    const { container } = render(<ShareAxis axisMax={0.35} />);
    expect(labels(container)).toEqual(['0%', '10%', '20%', '30%']);
  });
});
