package parser;

import com.github.javaparser.JavaParser;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.body.MethodDeclaration;
import com.github.javaparser.ast.comments.Comment;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVPrinter;
import org.apache.commons.csv.CSVRecord;

import java.io.IOException;
import java.io.Reader;
import java.io.Writer;
import java.nio.file.Files;
import java.nio.file.Paths;

public class MethodCodeWriter {
    private final static String path = System.getProperty("user.dir") + "/src/main/java/parser/";
    private final static String javaFilePath = path + "";


    public static void main(String[] args) throws IOException {
        try (Reader reader = Files.newBufferedReader(Paths.get(path + "db.csv"));
             CSVParser csvParser = new CSVParser(reader, CSVFormat.DEFAULT
                     .withFirstRecordAsHeader()
                     .withIgnoreHeaderCase()
                     .withTrim());
             Writer writer = Files.newBufferedWriter(Paths.get("method_db.csv"));
             CSVPrinter methodWriter = new CSVPrinter(writer, CSVFormat.DEFAULT
                     .withHeader("File", "Doc", "Code"))) {

            for (CSVRecord line : csvParser) {
                String fileHash = line.get("hash");

                CompilationUnit code = JavaParser.parse(Paths.get(javaFilePath + fileHash));
                for (MethodDeclaration method : code.findAll(MethodDeclaration.class)) {

                    String javadoc = "";
                    if (method.getJavadoc().isPresent()) {
                        javadoc = method.getJavadoc().get().getDescription().toText().split("\\R", 2)[0].toLowerCase();
                    }
                    method.removeJavaDocComment();
                    method.getAllContainedComments().forEach(Comment::remove);
                    String cleanedCode = method.toString().replaceAll("\\s+", " ");

                    methodWriter.printRecord(fileHash, javadoc, cleanedCode);
                }
            }

        }
    }
}
