declare module '*.png';
declare module '*.jpg';
declare module '*.gif';
declare module '*.svg';

declare module '*.mod.css' {
  const styles: { [className: string]: string };
  export default styles;
}
