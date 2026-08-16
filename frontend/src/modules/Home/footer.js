function Footer({ dead }) {
  return (
    <footer className={`homepage-footer ${dead ? 'homepage-footer--dead' : ''}`}>
      <p>Order of Elite © 2026, Los Angeles</p>
    </footer>
  );
}

export default Footer;
