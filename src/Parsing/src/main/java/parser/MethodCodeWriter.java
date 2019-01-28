package parser;

import com.github.javaparser.JavaParser;
import com.github.javaparser.ParseProblemException;
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
    private final static String path = "/home/jpsilva/corpus/";
    private final static String javaFilePath = path + "java/";


    public static void main(String[] args) throws IOException {
        int progress = 0;
        int classErrors = 0;
        int methodErrors = 0;

        try (Reader reader = Files.newBufferedReader(Paths.get(path + "db.csv"));
             CSVParser csvParser = new CSVParser(reader, CSVFormat.DEFAULT
                     .withFirstRecordAsHeader()
                     .withIgnoreHeaderCase()
                     .withTrim());
             Writer writer = Files.newBufferedWriter(Paths.get(path + "method_db.csv"));
             CSVPrinter methodWriter = new CSVPrinter(writer, CSVFormat.DEFAULT
                     .withHeader("file", "doc", "code"));
             Writer errorFileWriter = Files.newBufferedWriter(Paths.get(path + "errors.txt"))) {

            for (CSVRecord line : csvParser) {
                if (line.get("language").equals("java")) {

                    if (progress % 39670 == 0) {
                        System.out.println("Progress: " + progress / 39670 + "%, " + classErrors + " class errors, " + methodErrors + " method errors");
                    }

                    String fileHash = line.get("hash");

                    try {
                        CompilationUnit code = JavaParser.parse(Paths.get(javaFilePath + fileHash));
                        for (MethodDeclaration method : code.findAll(MethodDeclaration.class)) {
                            try {
                                String javadoc = "";
                                if (method.getJavadoc().isPresent()) {
                                    javadoc = method.getJavadoc().get().getDescription().toText().split("\\R", 2)[0].toLowerCase();
                                }
                                method.removeJavaDocComment();
                                method.getAllContainedComments().forEach(Comment::remove);
                                method.removeComment();
                                String cleanedCode = method.toString().replaceAll("\\s+", " ");

                                methodWriter.printRecord(fileHash, javadoc, cleanedCode);
                            } catch (RuntimeException e) {
                                methodErrors++;
                                errorFileWriter.write("METHOD ERROR: " + method.getName() + " " + fileHash + "\n");
                            }
                        }

                    } catch (ParseProblemException e) {
                        classErrors++;
                        errorFileWriter.write("PARSE ERROR: " + fileHash + "\n");
                    } catch (Exception e) {
                        System.out.println("Problem in file " + fileHash);
                        e.printStackTrace();
                    }
                    progress++;
                }
            }
        }
    }
}
